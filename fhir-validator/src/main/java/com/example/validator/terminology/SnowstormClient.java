package com.example.validator.terminology;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

/**
 * Tiny HTTP client for Snowstorm.
 *
 * What it does:
 * - validateSnomedCode(): calls Snowstorm's FHIR R4 $validate-code operation for SNOMED CT.
 * - conceptExistsNative(): alternative “native” check using Snowstorm’s browser API.
 *
 * Notes:
 * - This class is intentionally minimal: no retries, no timeouts, no auth.
 *   If you need production-hardening, consider adding those.
 * - Snowstorm exposes a FHIR **R4** API. That’s fine even if your app validates R5 resources,
 *   because we only ask Snowstorm to check SNOMED codes (system + code), which is version-agnostic.
 */
@Component
public class SnowstormClient {

  private static final Logger log = LoggerFactory.getLogger(SnowstormClient.class);

  /**
   * Base URL for Snowstorm.
   *
   * IMPORTANT:
   * - Here we expect the **root** Snowstorm URL (e.g. http://snowstorm:8080),
   *   because validateSnomedCode will append "/fhir/..." itself.
   * - If your configuration provides ".../fhir" already, either remove the "/fhir"
   *   in code below or change your property to the root.
   *
   * Env/property precedence:
   * - Spring property key: app.snowstorm.base
   * - Default value: http://snowstorm:8080
   */
  @Value("${app.snowstorm.base:http://snowstorm:8080}")
  private String base;

  /**
   * The SNOMED CT branch used by the native browser API call.
   * Common values:
   * - MAIN
   * - MAIN/SNOMEDCT-<COUNTRY>
   */
  @Value("${app.snowstorm.branch:MAIN}")
  private String branch;

  /**
   * Reusable Java 11+ HTTP client.
   * By default:
   * - Uses system proxy settings
   * - No custom timeouts (consider adding if needed)
   */
  private final HttpClient http = HttpClient.newHttpClient();

  /**
   * Validate a SNOMED code using FHIR R4 $validate-code.
   *
   * Request:
   *   POST {base}/fhir/CodeSystem/$validate-code
   *   Body (Parameters):
   *   {
   *     "resourceType": "Parameters",
   *     "parameter": [
   *       {"name":"url","valueUri":"http://snomed.info/sct"},
   *       {"name":"code","valueCode":"<code>"}
   *     ]
   *   }
   *
   * Expected response (200 OK):
   *   Parameters with a "result" boolean parameter:
   *   {
   *     "resourceType":"Parameters",
   *     "parameter":[
   *       {"name":"result","valueBoolean":true|false},
   *       {"name":"display","valueString":"..."},
   *       ...
   *     ]
   *   }
   *
   * Return:
   * - true  if HTTP is 2xx AND result==true
   * - false otherwise (including exceptions)
   */
  public boolean validateSnomedCode(String code) {
    try {
      // Build endpoint on the FHIR API
      String endpoint = base + "/fhir/CodeSystem/$validate-code";

      // Minimal Parameters body: we only pass the system URL and the code
      String body = """
        {
          "resourceType":"Parameters",
          "parameter":[
            {"name":"url","valueUri":"http://snomed.info/sct"},
            {"name":"code","valueCode":"%s"}
          ]
        }
      """.formatted(code);

      // Build POST request
      HttpRequest req = HttpRequest.newBuilder()
          .uri(URI.create(endpoint))
          .header("Content-Type","application/fhir+json")
          .header("Accept","application/fhir+json")
          .POST(HttpRequest.BodyPublishers.ofString(body))
          .build();

      // Log & send
      log.debug("Snowstorm $validate-code -> {}", endpoint);
      HttpResponse<String> resp = http.send(req, HttpResponse.BodyHandlers.ofString());
      log.debug("Snowstorm $validate-code status={} body={}", resp.statusCode(), resp.body());

      // Very lightweight parsing: check both 2xx and presence of result=true
      return resp.statusCode() / 100 == 2
          && resp.body().contains("\"name\":\"result\"")
          && resp.body().contains("\"valueBoolean\":true");
    } catch (Exception e) {
      // Do not fail validation pipeline on network errors; just report false and log
      log.warn("Snowstorm $validate-code failed for {}: {}", code, e.toString());
      return false;
    }
  }

  /**
   * Alternate check using Snowstorm’s native browser API (non-FHIR).
   * GET {base}/browser/{branch}/concepts/{code}
   *
   * Typical response (200 OK):
   * {
   *   "conceptId":"...",
   *   "active":true,
   *   ...
   * }
   *
   * Return:
   * - true  if HTTP 200 and "active": true appears in the JSON
   * - false for any other status or on exceptions
   *
   * Use cases:
   * - When you just need to know if the concept exists and is active on a branch,
   *   without FHIR-specific semantics.
   */
  public boolean conceptExistsNative(String code) {
    try {
      String url = base + "/browser/" + branch + "/concepts/" + code;

      HttpRequest req = HttpRequest.newBuilder()
          .uri(URI.create(url))
          .GET()
          .build();

      log.debug("Snowstorm native check -> {}", url);
      HttpResponse<String> resp = http.send(req, HttpResponse.BodyHandlers.ofString());

      if (resp.statusCode() == 200) {
        // Minimal check: treat as valid only if explicitly active
        return resp.body().contains("\"active\":true");
      }
      return false;
    } catch (Exception e) {
      log.warn("Snowstorm native check failed for {}: {}", code, e.toString());
      return false;
    }
  }
}
