package com.example.validator.config;

import ca.uhn.fhir.context.FhirContext;
import ca.uhn.fhir.parser.IParser;
import ca.uhn.fhir.validation.FhirValidator;

import ca.uhn.fhir.context.support.DefaultProfileValidationSupport;
import ca.uhn.fhir.narrative.DefaultThymeleafNarrativeGenerator;

import org.hl7.fhir.common.hapi.validation.support.*;
import org.hl7.fhir.common.hapi.validation.validator.FhirInstanceValidator;
import org.hl7.fhir.r5.utils.validation.constants.BestPracticeWarningLevel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;
import org.springframework.util.StringUtils;

import com.example.validator.validation.RequiredResourcesValidator;
import com.example.validator.validation.SnomedSnowstormValidator;

import java.io.IOException;

/**
 * Central configuration for the FHIR validator.
 *
 * This configuration:
 *  - Creates a FHIR R5 context
 *  - Builds a ValidationSupportChain with core R5 support, IG packages, and terminology helpers
 *  - Optionally adds a remote terminology fallback (tx.fhir.org)
 *  - Registers a custom SNOMED validator that talks to Snowstorm (R4) out-of-band
 *  - Exposes a JSON parser
 */
@Configuration
public class FhirValidatorConfig {

  private static final Logger log = LoggerFactory.getLogger(FhirValidatorConfig.class);

  /** Optional fallback terminology service base URL (e.g. https://tx.fhir.org/r4 or /r5). */
  @Value("${app.fhir.txBaseUrl:}")
  private String txBaseUrl;

  /** Comma-separated list of IG package paths to load from the classpath (NPM .tgz files). */
  @Value("${app.fhir.igClasspathPackages:}")
  private String igClasspathPackages;

  /**
   * R5 FHIR context used by the application.
   *
   * Notes:
   *  - ServerValidationMode is set to NEVER to avoid fetching/validating $metadata during client init.
   *  - Socket timeout is set to 30s for remote calls (e.g. terminology servers).
   */
  @Bean("r5Ctx")
  public FhirContext fhirContextR5() {
    FhirContext ctx = FhirContext.forR5();
    ctx.getRestfulClientFactory()
      .setServerValidationMode(ca.uhn.fhir.rest.client.api.ServerValidationModeEnum.NEVER);
    ctx.getRestfulClientFactory().setSocketTimeout(30000);
    ctx.setNarrativeGenerator(new DefaultThymeleafNarrativeGenerator());

    return ctx;
  }

  /**
   * Builds the ValidationSupportChain used by the FHIR instance validator.
   *
   * The chain contains (in order):
   *  0) IG packages loaded from the classpath (NpmPackageValidationSupport)
   *  1) DefaultProfileValidationSupport (Core R5 structures, profiles, value sets)
   *  2) InMemoryTerminologyServerValidationSupport (basic terminology ops without remote calls)
   *  3) CommonCodeSystemsTerminologyService (UCUM and other common code systems)
   *  4) SnapshotGeneratingValidationSupport (auto-generate snapshots for differential profiles)
   *  5) Optional remote terminology fallback (tx.fhir.org) — used for non-SNOMED lookups if configured
   *
   * Important:
   *  - SNOMED validation is NOT wired here (Snowstorm exposes R4 terminology).
   *    Instead, SNOMED codes are validated by a custom module (SnomedSnowstormValidator)
   *    that calls Snowstorm directly, avoiding R4/R5 mixing in the chain.
   */
  @Bean
  public ValidationSupportChain validationSupportChain(@Qualifier("r5Ctx") FhirContext ctxR5) {
    // 0) Load IG(s) from classpath with NPM package support
    NpmPackageValidationSupport npm = new NpmPackageValidationSupport(ctxR5);
    if (StringUtils.hasText(igClasspathPackages)) {
      for (String spec : igClasspathPackages.split(",")) {
        String normalized = spec.trim().replace("\\", "/");
        if (normalized.startsWith("classpath:")) normalized = normalized.substring("classpath:".length());
        if (normalized.startsWith("/")) normalized = normalized.substring(1);

        ClassPathResource res = new ClassPathResource(normalized);
        if (!res.exists()) {
          // Keep original Spanish messages to avoid changing behavior; only comments are in English.
          throw new IllegalStateException(
              "IG package not found in classpath: '" + normalized +
              "'. Place it in src/main/resources/" + normalized);
        }
        try {
          npm.loadPackageFromClasspath(normalized);
          log.info("Loaded IG from classpath:/{}", normalized);
        } catch (IOException e) {
          throw new IllegalStateException("Could not load IG from classpath: " + normalized, e);
        }
      }
    } else {
      log.info("No IG packages configured (app.fhir.igClasspathPackages empty)");
    }

    // 1) Base chain: core support + IG + terminology helpers
    ValidationSupportChain chain = new ValidationSupportChain();
    chain.addValidationSupport(new DefaultProfileValidationSupport(ctxR5));        // Core R5 structures/profiles
    chain.addValidationSupport(npm);                                              // Your IG packages
    chain.addValidationSupport(new InMemoryTerminologyServerValidationSupport(ctxR5));
    chain.addValidationSupport(new CommonCodeSystemsTerminologyService(ctxR5));   // UCUM, etc.
    chain.addValidationSupport(new SnapshotGeneratingValidationSupport(ctxR5));

    // 2) Optional fallback: remote terminology (tx.fhir.org) for non-SNOMED lookups
    //    Keep the base URL consistent with your FHIR version (e.g., /r4 or /r5).
    if (StringUtils.hasText(txBaseUrl)) {
      RemoteTerminologyServiceValidationSupport tx = new RemoteTerminologyServiceValidationSupport(ctxR5);
      tx.setBaseUrl(txBaseUrl); // e.g. https://tx.fhir.org/r4 or /r5 depending on your setup
      chain.addValidationSupport(tx);
      log.info("Fallback terminology added: {}", txBaseUrl);
    }

    return chain;
  }

  /**
   * Creates the FhirValidator (R5) and registers:
   *  - The standard FhirInstanceValidator backed by the ValidationSupportChain above
   *  - A custom SNOMED validator module that calls Snowstorm (R4 API) directly
   *
   * Why split SNOMED out?
   *  - Snowstorm currently exposes R4 FHIR terminology endpoints.
   *    Mixing R4 terminology support inside an R5 ValidationSupportChain causes version conflicts.
   *    By registering a separate custom validator module for SNOMED, we avoid version mixing
   *    while still validating SNOMED codes as part of a single validation pass.
   */
  @Bean
  public FhirValidator fhirValidator(
      @Qualifier("r5Ctx") FhirContext ctxR5,
      ValidationSupportChain chain,
      SnomedSnowstormValidator snomedModule, 
      RequiredResourcesValidator requiredResourcesModule
  ) {
    // Standard module using the chain
    FhirInstanceValidator module = new FhirInstanceValidator(chain);
    module.setAnyExtensionsAllowed(true);
    module.setBestPracticeWarningLevel(BestPracticeWarningLevel.Ignore);
    // Build the validator from the R5 context and register both modules
    FhirValidator validator = ctxR5.newValidator().registerValidatorModule(module);

    // Register the custom SNOMED module (talks to Snowstorm out-of-band)
    validator.registerValidatorModule(snomedModule);
    validator.registerValidatorModule(requiredResourcesModule);
    // Parallelize bundle validation to speed up multi-entry bundles
    validator.setConcurrentBundleValidation(true);
    return validator;
  }

  /**
   * A pretty-printing JSON parser bound to the R5 context.
   */
  @Bean
  public IParser jsonParser(@Qualifier("r5Ctx") FhirContext ctxR5) {
    return ctxR5.newJsonParser().setPrettyPrint(true);
  }
}
