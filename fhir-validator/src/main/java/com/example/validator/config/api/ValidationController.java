package com.example.validator.config.api;

import ca.uhn.fhir.parser.IParser;
import ca.uhn.fhir.validation.FhirValidator;
import ca.uhn.fhir.validation.ValidationResult;
import org.hl7.fhir.r5.model.Bundle;
import org.hl7.fhir.r5.model.DomainResource;
import org.hl7.fhir.r5.model.Narrative.NarrativeStatus;
import org.hl7.fhir.r5.model.OperationOutcome;
import org.hl7.fhir.r5.model.Resource;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;

/**
 * Simple REST controller exposing a validation endpoint.
 *
 * POST /api/validate/bundle
 *  - Accepts a JSON FHIR R5 Bundle as the request body
 *  - Validates it using the configured FhirValidator
 *  - Returns an OperationOutcome (as JSON) with issues/warnings/errors
 */
@RestController
@RequestMapping("/api/validate")
public class ValidationController {

  /** HAPI FHIR validator composed in configuration (R5 + custom SNOMED module). */
  private final FhirValidator validator;

  /** JSON parser bound to the same R5 FhirContext (configured in FhirValidatorConfig). */
  private final IParser json;

  public ValidationController(FhirValidator validator, IParser json) {
    this.validator = validator;
    this.json = json;
  }

  private static void ensureMinimalNarrative(org.hl7.fhir.instance.model.api.IBaseResource res) {
    if (res instanceof DomainResource dr) {
      boolean missing = !dr.hasText()
          || dr.getText().getDiv() == null
          || dr.getText().getDivAsString().trim().isEmpty();
      if (missing) {
        dr.getText().setStatus(NarrativeStatus.GENERATED);
        String type = dr.fhirType();
        String id = (res instanceof Resource r && r.hasIdElement()) ? r.getIdElement().getIdPart() : "";
        dr.getText().setDivAsString(
            "<div xmlns=\"http://www.w3.org/1999/xhtml\"><p>" +
                type + (id.isEmpty() ? "" : " " + id) +
            "</p></div>"
        );
      }
    }
  }

  /**
   * Validate a FHIR Bundle.
   *
   * @param bundleJson raw JSON string containing a FHIR R5 Bundle
   * @return OperationOutcome serialized as JSON (string)
   *
   * Notes:
   *  - We parse the incoming string into an R5 Bundle using the injected parser.
   *  - validator.validateWithResult(...) runs all registered validator modules.
   *  - ValidationResult#toOperationOutcome produces a standard OperationOutcome.
   *  - We serialize the OperationOutcome back to JSON and return it.
   */
  @PostMapping(
      value = "/bundle",
      consumes = MediaType.APPLICATION_JSON_VALUE,
      produces = MediaType.APPLICATION_JSON_VALUE
  )
  public String validateBundle(@RequestBody String bundleJson) {
    // Parse request JSON into a FHIR R5 Bundle resource
    Bundle bundle = (Bundle) json.parseResource(bundleJson);
        bundle.getEntry().forEach(e -> {
      if (e.hasResource()) {
        ensureMinimalNarrative(e.getResource());
      }
    });
    // Validate using the configured FhirValidator (core chain + custom SNOMED validator)
    ValidationResult vr = validator.validateWithResult(bundle);

    // Convert the result to a standard OperationOutcome
    OperationOutcome oo = (OperationOutcome) vr.toOperationOutcome();

    // Return the OperationOutcome JSON
    return json.encodeResourceToString(oo);
  }
}

