package com.example.validator.validation;

import ca.uhn.fhir.validation.IValidationContext;
import ca.uhn.fhir.validation.IValidatorModule;
import ca.uhn.fhir.validation.ResultSeverityEnum;
import ca.uhn.fhir.validation.SingleValidationMessage;

import org.hl7.fhir.instance.model.api.IBaseResource;
import org.hl7.fhir.r5.model.Bundle;
import org.hl7.fhir.r5.model.Resource;
import org.hl7.fhir.r5.model.ResourceType;
import org.springframework.stereotype.Component;

import java.util.EnumSet;
import java.util.Set;

@Component
public class RequiredResourcesValidator implements IValidatorModule {

  // Tipos mínimos exigidos en el Bundle
  private static final Set<ResourceType> REQUIRED = EnumSet.of(
      ResourceType.Patient, ResourceType.Encounter, ResourceType.Condition, ResourceType.Organization
  );

  public void validateResource(IValidationContext<IBaseResource> ctx) {
    Resource resource = (Resource) ctx.getResource();

    // Exigimos que el recurso raíz sea un Bundle con los tipos mínimos
    if (!(resource instanceof Bundle)) {
        addError(ctx, "The root resource must be a Bundle containing at least: Patient, Encounter, Condition, and Organization.");
      return;
    }

    Bundle bundle = (Bundle) resource;
    EnumSet<ResourceType> present = EnumSet.noneOf(ResourceType.class);

    bundle.getEntry().forEach(e -> {
      if (e.getResource() != null) {
        present.add(e.getResource().getResourceType());
      }
    });

    EnumSet<ResourceType> missing = EnumSet.copyOf(REQUIRED);
    missing.removeAll(present);

    if (!missing.isEmpty()) {
      addError(ctx, "Faltan recursos obligatorios en el Bundle: " + missing);
    }
  }

  private void addError(IValidationContext<?> ctx, String message) {
    SingleValidationMessage msg = new SingleValidationMessage();
    msg.setSeverity(ResultSeverityEnum.ERROR);
    msg.setMessage(message);
    ctx.addValidationMessage(msg);
  }
}
