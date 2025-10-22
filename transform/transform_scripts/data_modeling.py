from ast import List
from zoneinfo import ZoneInfo
from fhir.resources.organization import Organization
from fhir.resources.patient     import Patient
from fhir.resources.bundle      import Bundle, BundleEntryRequest
from fhir.resources.observation import Observation, ObservationComponent
from fhir.resources.encounter  import Encounter, EncounterAdmission
from fhir.resources.condition   import Condition
from fhir.resources.coding      import Coding
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.reference   import Reference
from fhir.resources.patient import Patient
from fhir.resources.procedure import Procedure
from fhir.resources.extension import Extension
from fhir.resources.medicationstatement import MedicationStatement, MedicationStatementAdherence
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.period import Period
from fhir.resources.identifier import Identifier
from direct_mapping import *
from datetime import datetime
from enum_models import *
import direct_mapping as maps
import pandas as pd
import uuid
from provider_map import mapping as provider_mapping

class TransformError(ValueError):
    """Raised when input data is invalid or inconsistent for FHIR transformation."""

def safe_get(raw: dict, key: str, *, required: bool = False, ctx: str = ""):
    """Get a value from raw with an optional requirement and nice error if missing."""
    if key in raw and raw[key] is not None:
        return raw[key]
    if required:
        where = f" while {ctx}" if ctx else ""
        raise TransformError(f"Missing required field '{key}'{where}.")
    return None

def by_id_or_error(enum_cls, value, *, field: str, ctx: str = ""):
    """Call Enum.by_id with clear error messages."""
    try:
        return enum_cls.by_id(str(value))
    except Exception as e:
        where = f" while {ctx}" if ctx else ""
        raise TransformError(
            f"Invalid value '{value}' for field '{field}'{where}. "
            f"Expected a valid identifier for {enum_cls.__name__}. Underlying error: {e}"
        )

def ensure_dependency(condition: bool, *, need: str, because: str):
    if not condition:
        raise TransformError(
            f"Prerequisite missing: {need} is required because {because}."
        )

def safe_isna(x) -> bool:
    try:
        import pandas as _pd
        return bool(_pd.isna(x))
    except Exception:
        return x is None

def parse_datetime(raw: str, *, tz: str = "Europe/Bratislava") -> datetime:
    """Parse datetime with informative error."""
    if raw is None or str(raw).strip() == "":
        raise TransformError("Datetime value is empty.")
    raw = str(raw).strip()
    tried = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]
    last_err = None
    for fmt in tried:
        try:
            dt = datetime.strptime(raw, fmt)
            # If only date, assume midnight
            if fmt == "%Y-%m-%d":
                dt = datetime.combine(dt.date(), datetime.min.time())
            return dt.replace(tzinfo=ZoneInfo(tz))
        except Exception as e:
            last_err = e
    raise TransformError(
        f"Invalid datetime '{raw}'. Expected one of formats {tried}. Underlying error: {last_err}"
    )

def get_uuid() -> str:
    return f"urn:uuid:{uuid.uuid4()}"


def get_stroke_etiology(raw: dict):
    # No error if none applies; choose first True
    if raw.get("stroke_etiology_cardioembolism") is True:
        return StrokeEtiology.by_id("Cardioembolism")
    if raw.get("stroke_etiology_la_atherosclerosis") is True:
        return StrokeEtiology.by_id("Atherosclerosis")
    if raw.get("stroke_etiology_lacunar") is True:
        return StrokeEtiology.by_id("Lacunar")
    if raw.get("stroke_etiology_cryptogenic_stroke") is True:
        return StrokeEtiology.by_id("Cryptogenic Stroke")
    if raw.get("stroke_etiology_other") is True:
        return StrokeEtiology.by_id("Other")
    return None

def get_before_onset_medications(raw: dict):
    medications_taken = []
    medications_not_taken = []
    medications_unknown = []

    mapping = {
        "before_onset_antidiabetics": BeforeOnsetMedication.ANTIDIABETIC,
        "before_onset_antihypertensives": BeforeOnsetMedication.ANTIHYPERTENSIVE,
        "before_onset_any_anticoagulant": BeforeOnsetMedication.ANTICOAGULANT,
        "before_onset_any_antiplatelet": BeforeOnsetMedication.ANTIPLATELET,
        "before_onset_asa": BeforeOnsetMedication.ASA,
        "before_onset_clopidogrel" : BeforeOnsetMedication.CLOPIDOGREL,
        "before_onset_contraception": BeforeOnsetMedication.CONTRACEPTION,
        "before_onset_other_anticoagulant": BeforeOnsetMedication.ANTICOAGULANT,
        "before_onset_statin": BeforeOnsetMedication.STATIN,
        "before_onset_warfarin": BeforeOnsetMedication.WARFARIN
        
    }

    for key, med in mapping.items():
        value = raw.get(key)
        if value is True:
            medications_taken.append(med)
        elif value is False:
            medications_not_taken.append(med)
        elif pd.isna(value):
            medications_unknown.append(med)

    return medications_taken, medications_not_taken, medications_unknown


def get_on_discharge_medications(raw: dict):
    medications_prescribed = []

    mapping = {
        "discharge_antidiabetics": DischargeMedication.ANTIDIABETIC,
        "discharge_antihypertensives": DischargeMedication.ANTIHYPERTENSIVE,
        "discharge_any_anticoagulant": DischargeMedication.ANTICOAGULANT,
        "discharge_any_antiplatelet": DischargeMedication.ANTIPLATELET,
        "discharge_other_antiplatelet": DischargeMedication.OTHER_ANTIPLATELET,
        "discharge_herparin": DischargeMedication.HEPARIN,
        "discharge_asa": DischargeMedication.ASPIRIN,
        "discharge_clopidogrel": DischargeMedication.CLOPIDOGREL,
        "discharge_contraception": DischargeMedication.CONTRACEPTION,
        "discharge_other": DischargeMedication.OTHER,
        "discharge_statin": DischargeMedication.STATIN,
        "discharge_warfarin": DischargeMedication.WARFARIN

    }

    for key, med in mapping.items():
        value = raw.get(key)
        if value is True:
            medications_prescribed.append(med)

    return medications_prescribed


def get_bleeding_reason(raw: dict):
    if raw.get("bleeding_reason_aneurysm") is True:
        return BleedingReason.by_id("Aneurysm")
    if raw.get("bleeding_reason_malformation") is True:
        return BleedingReason.by_id("Malformation")
    if raw.get("bleeding_reason_other") is True:
        return BleedingReason.by_id("Other")
    return None

def get_risk_factors(raw: dict):
    risk_factor_active = []
    risk_factor_inactive = []
    risk_factor_unknown = []
    risk_factor_remission = []
    mapping = {
        "risk_hypertension": RiskFactor.Hypertension,
        "risk_diabetes": RiskFactor.Diabetes,
        "risk_hyperlipidemia": RiskFactor.Hyperlipidemia,
        "risk_previous_stroke": RiskFactor.PreviousStroke,
        "risk_previous_ischemic_stroke": RiskFactor.PreviousIschemicStroke,
        "risk_previous_hemorrhagic_stroke" : RiskFactor.PreviousHemorrahagicStroke,
        "risk_atrial_fibrillation": RiskFactor.AtrialFibrillation,
        "risk_coronary_artery_disease_or_myocardial_infarction": RiskFactor.CoronaryArteryDisease,
    }

    for key, med in mapping.items():
        value = raw.get(key)
        print(key)
        print(raw.get(key))
        print()
        if value is True:
            if med.id == "PreviousIschemicStroke" or med.id == "PreviousHemorraghicStroke" or med.id == "PreviousStroke":
                risk_factor_remission.append(med)
            else:
                risk_factor_active.append(med)
        elif value is False:
            risk_factor_inactive.append(med)
        elif pd.isna(value):
            risk_factor_unknown.append(med)

    return risk_factor_active, risk_factor_inactive, risk_factor_unknown, risk_factor_remission

def build_Patient(raw: dict) -> Patient:
    patient = Patient()
    patient.id = str(raw["id"])
    extension_list = []

    # Gender (optional)
    sex_id = raw.get("sex_id")
    if sex_id is not None and str(sex_id).strip() != "":
        try:
            sex = Sex.by_id(str(sex_id))
            coding_gender = Coding(system=getattr(sex, "system", None),
                                   code=getattr(sex, "code", None),
                                   display=str(getattr(sex, "display", "")))
            code_gender = CodeableConcept(coding=[coding_gender])
            extension_list.append(Extension(
                url="http://testSK.org/StructureDefinition/gender-snomed-ext",
                valueCodeableConcept=code_gender
            ))
        except Exception as e:
            raise TransformError(
                f"Invalid 'sex_id' value '{sex_id}'. Expected a valid Sex id. Underlying error: {e}"
            )
    if extension_list:
        patient.extension = extension_list
    return patient

def build_stroke_diagnosis_condition_profile(raw: dict, patient_ref: str, encounter_ref: str) -> Condition:
    condition = Condition(subject=Reference(reference=patient_ref),
                          clinicalStatus=CodeableConcept(),
                          encounter=Reference(reference=encounter_ref))

    # Required: stroke_type_id (caller guarantees presence, but we validate)
    stroke_type_id = safe_get(raw, "stroke_type_id", required=True, ctx="building Stroke Condition")
    stroke = by_id_or_error(StrokeType, stroke_type_id, field="stroke_type_id", ctx="building Stroke Condition")

    # code (Stroke type)
    condition.code = CodeableConcept(coding=[Coding(system=stroke.system, code=stroke.code, display=stroke.display)])

    # statuses
    condition.clinicalStatus = CodeableConcept(coding=[Coding(
        system="http://terminology.hl7.org/CodeSystem/condition-clinical", code="active", display="Active"
    )])
    condition.verificationStatus = CodeableConcept(coding=[Coding(
        system="http://terminology.hl7.org/CodeSystem/condition-ver-status", code="confirmed", display="Confirmed"
    )])

    # Profile + optional extensions
    condition.meta = {"profile": ["http://testSK.org/StructureDefinition/stroke-diagnosis-condition-profile"]}
    extension_list = []

    etiology = get_stroke_etiology(raw)
    bleeding_reason = get_bleeding_reason(raw)

    if etiology is not None:
        extension_list.append(Extension(
            url="http://testSK.org/StructureDefinition/ischemic-stroke-etiology-ext",
            valueCodeableConcept=CodeableConcept(coding=[Coding(system=etiology.system, code=etiology.code, display=etiology.display)])
        ))
    elif bleeding_reason is not None:
        extension_list.append(Extension(
            url="http://testSK.org/StructureDefinition/hemorrhagic-stroke-bleeding-reason-ext",
            valueCodeableConcept=CodeableConcept(coding=[Coding(system=bleeding_reason.system, code=bleeding_reason.code, display=bleeding_reason.display)])
        ))

    # onset date/time (optional, but defensive)
    if not safe_isna(raw.get('onset_date')):
        extension_list.append(Extension(url="http://testSK.org/StructureDefinition/onset-date-ext",
                                        valueDate=raw['onset_date'].date().isoformat()))
    if not safe_isna(raw.get('onset_time')):
        extension_list.append(Extension(url="http://testSK.org/StructureDefinition/onset-time-ext",
                                        valueTime=raw['onset_time'].time().isoformat()))

    if extension_list:
        condition.extension = extension_list

    return condition


def build_risk_factor_condition_profile(raw, patient_ref : str, encounter_ref : str):

    risk_factor_active, risk_factor_inactive, risk_factor_unknown, risk_factor_remission = get_risk_factors(raw)
    final_rf_list = []
    grouped = [("Active", risk_factor_active), ("Inactive", risk_factor_inactive), ("Unknown",risk_factor_unknown), ("Remission", risk_factor_remission)]
    for status_key, rf in grouped:
        # Build condition core attributes
        # Create a code for risk factor
        clinicalStatus = ClinicalStatusCodes.by_id(status_key)
        coding_status = Coding(system=clinicalStatus.system, code=clinicalStatus.code, display=clinicalStatus.display)
        code_status = CodeableConcept(coding=[coding_status])
        for r in rf:
            coding_rf = Coding(system=r.system, code=r.code, display=r.display)
            code_rf = CodeableConcept(coding=[coding_rf])
            
            condition = Condition(
            
            subject = Reference(reference=patient_ref),
            code = code_rf,
            meta = {"profile": ["http://testSK.org/StructureDefinition/stroke-risk-factor-condition-profile"]},
            clinicalStatus = code_status,
            encounter = Reference(reference=encounter_ref),
            )
            if r.id == "AtrialFibrillation":
                condition.verificationStatus = CodeableConcept(coding=[Coding(
                    system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    code="differential",
                    display="Differential"
                )])
            final_rf_list.append(condition)
        
    return final_rf_list


def build_imaging_procedure(raw: dict, patient_ref : str, encounter_ref : str) -> Procedure:
    #—————————————
    #     # 3) Procedure: ImagingDone
    #     # —————————————
    procedure_final = Procedure(subject=Reference(reference=patient_ref), encounter=Reference(reference=encounter_ref), status="completed")
    imaging_done = ImagingDone.by_id(str(raw["imaging_done_id"]))
    if imaging_done == ImagingDone.YES:
        status_coding = Coding(
            system = "http://hl7.org/fhir/event-status",
            code = "completed",
            display = "Completed"
        )
        status_reason = None
        procedure_final.status = "completed"
    else:
        if imaging_done == ImagingDone.NO:
            status_reason = ProcedureNotDoneReason.UNKNOWN
        elif imaging_done == ImagingDone.ELSEWHERE:
            status_reason = ProcedureNotDoneReason.DONE_ELSEWHERE
        status_coding = Coding(
            system = "http://hl7.org/fhir/event-status",
            code = "not-done",
            display = "Not Done"
        )
        procedure_final.status = "not-done"
        if status_reason is not None:
            status_reason_coding = Coding(
                system = status_reason.system,
                code = status_reason.code,
                display = status_reason.display
            )
            status_reason_code = CodeableConcept(coding=[status_reason_coding])
            procedure_final.statusReason = status_reason_code
         
    imaging_code = ImagingType.by_id(str(raw["imaging_type_id"]))
    coding_imaging = Coding(
        code = imaging_code.code,
        system = imaging_code.system,
        display = imaging_code.display
    )
    code_imaging = CodeableConcept(coding=[coding_imaging])

    procedure_final.code = code_imaging
    category_coding = Coding(
        system = "http://terminology.hl7.org/CodeSystem/observation-category",
        code = "imaging",
        display = "Imaging"
    )
    category_code = CodeableConcept(coding=[category_coding])
    procedure_final.category = [category_code]
    post_acute_care = PostAcuteCare.by_id(str(raw.get("post_acute_care")))
    post_acute_care_coding = Coding(
        code = post_acute_care.code,
        system = post_acute_care.system,
        display = post_acute_care.display
    )
    post_acute_care_code = CodeableConcept(coding=[post_acute_care_coding])

    extension_list = []
    extension_list.append(Extension(url="http://testSK.org/StructureDefinition/procedure-timing-context-ext", valueCodeableConcept=post_acute_care_code))
    category_code = CodeableConcept(coding=[category_coding])
    procedure_final.extension = extension_list
    imaging_timestamp = raw.get("imaging_timestamp")
    if imaging_timestamp is not None:
        imaging_timestamp = parse_datetime(str(imaging_timestamp))
        procedure_final.occurrenceDateTime = imaging_timestamp        
        return procedure_final
    return procedure_final

def build_observation_Af_or_F(raw: dict, patient_ref: str, encounter_ref: str) -> Observation:
    af_value_id = safe_get(raw, "atrial_fibrillation_or_flutter_id", required=True,
                           ctx="building Atrial Fibrillation/Flutter Observation")
    af_value = by_id_or_error(AtrialFibrillationOrFlutter, af_value_id,
                              field="atrial_fibrillation_or_flutter_id",
                              ctx="building Atrial Fibrillation/Flutter Observation")

    af_stroke = RiskFactor.AtrialFibrillation
    af_stroke_code = CodeableConcept(coding=[Coding(system=af_stroke.system, code=af_stroke.code, display=af_stroke.display)])

    observation = Observation(code=af_stroke_code, status="final",
                              subject=Reference(reference=patient_ref),
                              encounter=Reference(reference=encounter_ref))
    observation.meta = {"profile": ["http://testSK.org/StructureDefinition/specific-finding-observation-profile"]}

    category = CodeableConcept(coding=[Coding(
        code="laboratory", display="Laboratory",
        system="http://terminology.hl7.org/CodeSystem/observation-category"
    )])

    observation.valueCodeableConcept = CodeableConcept(coding=[Coding(
        system=af_value.system, code=af_value.code, display=af_value.display
    )])
    observation.category = [category]

    if not safe_isna(raw.get("hospital_timestamp")):
        observation.effectiveDateTime = parse_datetime(str(raw["hospital_timestamp"]))
    return observation


def build_observation_vital_signs(raw: dict, patient_ref : str, encounter_ref : str) -> Observation:

    systolic = VitalSigns.by_id("Systolic")
    diastolic = VitalSigns.by_id("Diastolic")
    coding_systolic = Coding(
        code = systolic.code,
        system = systolic.system,
        display = systolic.display
    )
    
    code_systolic = CodeableConcept(coding=[coding_systolic])
    coding_diastolic = Coding(
        code = diastolic.code,
        system = diastolic.system,
        display = diastolic.display
    )
    code_systolic = CodeableConcept(coding=[coding_systolic])
    code_diastolic = CodeableConcept(coding=[coding_diastolic])
    category_coding = Coding(
        system = "http://terminology.hl7.org/CodeSystem/observation-category",
        code = "vital-signs",
        display = "Vital Signs"
    )

    category_code = CodeableConcept(coding=[category_coding])
    
    code_vs = VitalSigns.by_id("Take VS")
    coding_vs = Coding(
        code = code_vs.code,
        system = code_vs.system,
        display = code_vs.display
    )
    code_vs = CodeableConcept(coding=[coding_vs])
            

    component_systolic = ObservationComponent(
        code = code_systolic,
        valueQuantity={
            "value": raw.get("systolic_pressure"),
            "unit": UnitofMeasurement.MMGM.display,
            "system": UnitofMeasurement.MMGM.system,
            "code": UnitofMeasurement.MMGM.code
        }
    )
    component_diastolic = ObservationComponent(
        code = code_diastolic,
        valueQuantity={
            "value": raw.get("diastolic_pressure"),
            "unit": UnitofMeasurement.MMGM.display,
            "system": UnitofMeasurement.MMGM.system,
            "code": UnitofMeasurement.MMGM.code
        }
    )
    return Observation(
        status="final",
        #id = f"{patient.id}-obs-vital-signs",
        
        subject = Reference(reference=patient_ref),
        category = [category_code],
        code = code_vs,
        meta = {"profile": ["http://testSK.org/StructureDefinition/vital-sign-observation-profile"]},
        component = [component_systolic, component_diastolic],
        encounter = Reference(reference=encounter_ref),
    )
    

def build_observation_mrs(raw: dict, patient_ref : str, encounter_ref : str, prestroke: bool = False, discharge: bool = False, threem: bool = False) -> Observation:
    if prestroke:
        mrs_score = MRsScore.by_id(str(raw.get("prestroke_mrs")))
        assessment_value = AssessmentContext.PRESTROKE

    elif discharge:
        assessment_value = AssessmentContext.DISCHARGE
        mrs_score = MRsScore.by_id(str(raw.get("discharge_mrs")))
    elif threem:
        mrs_score = MRsScore.by_id(str(raw.get("three_m_mrs")))
        assessment_value = AssessmentContext.THREE_MONTHS


    assessment_coding = Coding(
            system = assessment_value.system,
            code = assessment_value.code,
            display = assessment_value.display
        )

    assessment_code = CodeableConcept(coding=[assessment_coding])

    extensions = Extension(url="http://testSK.org/StructureDefinition/observation-timing-context-ext",valueCodeableConcept=assessment_code)
    obs_code = FunctionalScore.MRS

    coding_mrs = Coding(
        code = obs_code.code,
        system = obs_code.system,
        display = obs_code.display
    )
    code_mrs = CodeableConcept(coding=[coding_mrs])
    
    coding_category = Coding(
        system = "http://terminology.hl7.org/CodeSystem/observation-category",
        code = "exam",
        display = "Exam"
    )
    code_category = CodeableConcept(coding=[coding_category])

    coding_value_mrs = Coding(
        system = mrs_score.system,
        code = mrs_score.code,
        display = mrs_score.display
    )

    code_value_mrs = CodeableConcept(coding=[coding_value_mrs])
    return Observation(
            status="final",
            
            meta = {"profile": ["http://testSK.org/StructureDefinition/functional-score-observation-profile"]},
            subject=Reference(reference=patient_ref),
            encounter=Reference(reference=encounter_ref),
            code = code_mrs,
            valueCodeableConcept= code_value_mrs,
            category=[code_category],
            extension=[extensions],
        )



def build_observation_nihss(raw: dict, patient_ref : str, encounter_ref : str, admission: bool = False, discharge: bool = False) -> Observation:

    if admission:
        assesment_value = AssessmentContext.ADMISSION
    elif discharge:
        assesment_value = AssessmentContext.DISCHARGE

    assesment_coding = Coding(
            system = assesment_value.system,
            code = assesment_value.code,
            display = assesment_value.display
        )
    extensions = Extension(url="http://testSK.org/StructureDefinition/observation-timing-context-ext",valueCodeableConcept=CodeableConcept(coding=[assesment_coding]))

    obs_code = FunctionalScore.NIHSS
    coding_nihss = Coding(
        code = obs_code.code,
        system = obs_code.system,
        display = obs_code.display
    )
    code_nihss = CodeableConcept(coding=[coding_nihss])
    coding_category = Coding(
        system = "http://terminology.hl7.org/CodeSystem/observation-category",
        code = "exam",
        display = "Exam"
    )
    code_category = CodeableConcept(coding=[coding_category])

    return Observation(
        status="final",
        
        subject=Reference(reference=patient_ref),
        encounter=Reference(reference=encounter_ref),
        meta = {"profile": ["http://testSK.org/StructureDefinition/functional-score-observation-profile"]},
        code=code_nihss,
        valueInteger=raw.get("nihss_score"),
        category=[code_category],
        extension=[extensions],
    )

def build_observation_mtici_score(raw: dict, patient_ref : str, encounter_ref : str) -> Observation:
#     # —————————————————————————
#     # 5) Observation: mTICI Score (si existe)
#     # —————————————————————————
    specific_finding = SpecificFinding.MTICI
    coding_mtici = Coding(
        code = specific_finding.code,
        system = specific_finding.system,
        display = specific_finding.display
    )
    code_mtici = CodeableConcept(coding=[coding_mtici])

    coding_category = Coding(
        system = "http://terminology.hl7.org/CodeSystem/observation-category",
        code = "survey",
        display = "Survey"
    )
    code_category = CodeableConcept(coding=[coding_category])

    mtici_score = MTiciScore.by_id(str(raw.get("mtici_score")))
    coding_value_mtici = Coding(
        system = mtici_score.system,
        code = mtici_score.code,
        display = mtici_score.display
    )
    code_value_mtici = CodeableConcept(coding=[coding_value_mtici])
    return Observation(
        status="final",
        
        subject=Reference(reference=patient_ref),
        meta={"profile": ["http://testSK.org/StructureDefinition/timing-metric-observation-profile"]},
        code=code_mtici,
        valueCodeableConcept=code_value_mtici,
        category=code_category.coding,
        encounter=Reference(reference=encounter_ref)
    )


def build_observation_smoking(raw: dict, patient_ref: str, encounter_ref: str) -> Observation:
    smoker_coding = Coding(
        code = RiskFactor.Smoker.code,
        system = RiskFactor.Smoker.system,
        display = RiskFactor.Smoker.display
    )

    code_smoker = CodeableConcept(coding=[smoker_coding])

    
    return Observation(
        status="final",
        subject=Reference(reference=patient_ref),
        meta={"profile": ["http://testSK.org/StructureDefinition/base-stroke-observation"]},
        code=code_smoker,
        encounter=Reference(reference=encounter_ref),
    )

def build_stroke_circumstance_observation(patient_ref : str, encounter_ref : str, condition_ref : str, wake_up = False, in_hosp = False) -> Observation:
    if wake_up:
        circumstance = StrokeCircumstance.WAKE_UP
    elif in_hosp:
        circumstance = StrokeCircumstance.IN_HOSPITAL
    
    circumstance_coding = Coding(
        code = circumstance.code,
        system = circumstance.system,
        display = circumstance.display
    )
    code_circumstance = CodeableConcept(coding=[circumstance_coding])
    return Observation(
        status="final",
        
        subject=Reference(reference=patient_ref),
        meta={"profile":["http://testSK.org/StructureDefinition/stroke-circumstance-observation-profile"]},
        code=code_circumstance,
        encounter=Reference(reference=encounter_ref),
        focus=[Reference(reference=condition_ref)]
    )


def build_carotid_imaging_procedure(raw: dict, patient_ref : str, encounter_ref:str, done_value) -> Procedure:

    procedure = Procedure(subject=Reference(reference=patient_ref), encounter=Reference(reference=encounter_ref), status="completed", meta={"profile": ["http://testSK.org/StructureDefinition/stroke-carotid-imaging-procedure-profile"]})
    carotid_imaging = CarotidImaging.CAROTID
    coding_carotid = Coding(
        code = carotid_imaging.code,
        system = carotid_imaging.system,
        display = carotid_imaging.display
    )
    code_carotid = CodeableConcept(coding=[coding_carotid])
    post_acute_care = PostAcuteCare.by_id(str(raw.get("post_acute_care")))
    coding_post_acute = Coding(
        code = post_acute_care.code,
        system = post_acute_care.system,
        display = post_acute_care.display
    )
    code_post_acute = CodeableConcept(coding=[coding_post_acute])
    extension_list = [Extension(url="http://testSK.org/StructureDefinition/procedure-timing-context-ext",valueCodeableConcept=code_post_acute)]
    
    if done_value:
        status_value = "completed"
    elif not done_value:
        status_value = "not-done"
        coding_status_reason = Coding(
            system = ProcedureNotDoneReason.UNKNOWN.system,
            code = ProcedureNotDoneReason.UNKNOWN.code,
            display = ProcedureNotDoneReason.UNKNOWN.display)
        code_status_reason = CodeableConcept(coding=[coding_status_reason])
        procedure.statusReason = code_status_reason
    else:
        status_value = "unknown"

    procedure.status = status_value
    procedure.extension= extension_list
    procedure.code = code_carotid

    return procedure
    

def build_swallowing_screening_procedure(raw: dict, patient_ref : str, encounter_ref : str) -> Procedure:

    procedure = Procedure(status="completed", subject=Reference(reference=patient_ref), encounter=Reference(reference=encounter_ref))
    procedure.meta = {"profile": ["http://testSK.org/StructureDefinition/stroke-swallow-procedure-profile"]}
    
    swallowing_screening = SwallowingScreeningDone.by_id(str(raw.get("swallowing_screening_done_id")))
    if swallowing_screening.id is "Yes":
        procedure.status = "completed"
    elif swallowing_screening.id is "No":
        procedure.status = "not-done"
        status_reason = ProcedureNotDoneReason.UNKNOWN
        status_reason_coding = Coding(
                system = status_reason.system,
                code = status_reason.code,
                display = status_reason.display
            )
        status_reason_code = CodeableConcept(coding=[status_reason_coding])
        procedure.statusReason = status_reason_code
    else:
        procedure.status = "unknown"

    if procedure.status == "completed":
        swallowing_type = SwallowingScreeningType.by_id(str(raw.get("swallowing_screening_type_id")))
        coding_type = Coding(
                code = swallowing_type.code,
                system = swallowing_type.system,
                display = swallowing_type.display
            )
        code_type = CodeableConcept(coding=[coding_type])
        
        procedure.code = code_type

        extension_list = []
        swallowing_timing = SwallowingScreeningTiming.by_id(str(raw.get("swallowing_screening_timing_id")))
        coding_result = Coding(
            code = swallowing_timing.code,
            system = swallowing_timing.system,
            display = swallowing_timing.display
        )
        code_result = CodeableConcept(coding=[coding_result])
        extension_list.append(Extension(url="http://testSK.org/StructureDefinition/swallowing-screening-timing-category-ext", valueCodeableConcept=code_result))
        
        post_acute_care = PostAcuteCare.by_id(str(raw.get("post_acute_care"))) 
        coding_post_acute = Coding(
            code = post_acute_care.code,
            system = post_acute_care.system,
            display = post_acute_care.display
        )
        code_post_acute = CodeableConcept(coding=[coding_post_acute])
        extension_list.append(Extension(url="http://testSK.org/StructureDefinition/procedure-timing-context-ext",valueCodeableConcept=code_post_acute))
        
        if len(extension_list) > 0:
            procedure.extension = extension_list
    
    procedure.subject = Reference(reference=patient_ref)
    procedure.encounter = Reference(reference=encounter_ref)
    return procedure


def build_thrombolysis_procedure(raw: dict, patient_ref : str, encounter_ref : str) -> Procedure:

    procedure = Procedure(status= "completed", subject=Reference(reference=patient_ref), encounter=Reference(reference=encounter_ref))
    procedure.meta = {"profile": ["http://testSK.org/StructureDefinition/stroke-mechanical-procedure-profile"]}
    thrombolysis = PerforationProcedures.THROMBOLYSIS
    coding_thrombolysis = Coding(
        code = thrombolysis.code,
        system = thrombolysis.system,
        display = thrombolysis.display
    )
    code_thrombolysis = CodeableConcept(coding=[coding_thrombolysis])
    procedure.code = code_thrombolysis
    extension_list = []
        
    if not pd.isna(raw.get("post_acute_care")):
        post_acute_care = PostAcuteCare.by_id(str(raw.get("post_acute_care")))
        coding_post_acute = Coding(
            code = post_acute_care.code,
            system = post_acute_care.system,
            display = post_acute_care.display
        )
        code_post_acute = CodeableConcept(coding=[coding_post_acute])
        extension_list.append(Extension(url="http://testSK.org/StructureDefinition/procedure-timing-context-ext",valueCodeableConcept=code_post_acute))
    
    if len(extension_list) > 0:
        procedure.extension = extension_list
    
    if raw.get("thrombolysis"):
        bolus_timestamp = raw.get("bolus_timestamp")
        if bolus_timestamp is not None:
            bolus_timestamp = parse_datetime(str(bolus_timestamp))
            procedure.occurrencePeriod=Period(start=bolus_timestamp)
        return procedure
    else:
        no_thrombolysis_reason = ProcedureNotDoneReason.by_id(str(raw.get("no_thrombolysis_reason_id")))
        coding_reason = Coding(
            code = no_thrombolysis_reason.code,
            system = no_thrombolysis_reason.system,
            display = no_thrombolysis_reason.display
        )
        code_reason = CodeableConcept(coding=[coding_reason])
        procedure.status = "not-done"
        procedure.statusReason = code_reason
        return procedure

def build_thrombectomy_procedure(raw: dict, patient_ref : str, encounter_ref : str, condition_ref : str) -> Procedure:
    procedure = Procedure(status= "not-done", subject=Reference(reference=patient_ref), encounter=Reference(reference=encounter_ref))
    procedure.meta = {"profile": ["http://testSK.org/StructureDefinition/stroke-mechanical-procedure-profile"]}
    thrombectomy = PerforationProcedures.THROMBECTOMY
    coding_thrombectomy = Coding(
        code = thrombectomy.code,
        system = thrombectomy.system,
        display = thrombectomy.display
    )
    code_thrombectomy = CodeableConcept(coding=[coding_thrombectomy])
    procedure.code = code_thrombectomy

    extension_list = []
        
    if not pd.isna(raw.get("post_acute_care")):
        post_acute_care = PostAcuteCare.by_id(str(raw.get("post_acute_care")))
        coding_post_acute = Coding(
            code = post_acute_care.code,
            system = post_acute_care.system,
            display = post_acute_care.display
        )
        code_post_acute = CodeableConcept(coding=[coding_post_acute])
        extension_list.append(Extension(url="http://testSK.org/StructureDefinition/procedure-timing-context-ext",valueCodeableConcept=code_post_acute))
    
    if len(extension_list) > 0:
        procedure.extension = extension_list

    if raw.get("thrombectomy"):
        procedure.status = "completed"  
        puncture_timestamp = raw.get("puncture_timestamp")
        reperfusion_timestamp = raw.get("reperfusion_timestamp")
        if puncture_timestamp is not None and reperfusion_timestamp is not None:
            puncture_timestamp = parse_datetime(str(puncture_timestamp))
            reperfusion_timestamp = parse_datetime(str(reperfusion_timestamp))
            procedure.occurrencePeriod = Period(start=puncture_timestamp, end=reperfusion_timestamp)

    if not pd.isna(raw.get("mt_complications_perforation")):
        perforation = ThrombectomyComplications.PERFORATION
        coding_perforation = Coding(
            code = perforation.code,
            system = perforation.system,
            display = perforation.display
        )
        code_perforation = CodeableConcept(coding=[coding_perforation])
        code_ref_perforation = CodeableReference(concept=code_perforation, reference=Reference(reference=condition_ref))
        procedure.complication = [code_ref_perforation]
        return procedure
    else:
        no_thrombectomy_reason = ProcedureNotDoneReason.by_id(str(raw.get("no_thrombectomy_reason_id")))
        coding_reason = Coding(
            code = no_thrombectomy_reason.code,
            system = no_thrombectomy_reason.system,
            display = no_thrombectomy_reason.display
        )
        code_reason = CodeableConcept(coding=[coding_reason])

        procedure.statusReason = code_reason
        return procedure

def build_stroke_encounter_profile(raw: dict, patient_ref : str) -> Encounter:

    # We build the Encounter resource
    encounter = Encounter(status="completed", subject=Reference(reference=patient_ref))
    encounter.meta = {"profile" : ["http://testSK.org/StructureDefinition/stroke-encounter-profile"]}

    # Obtain discharge destination and arrival mode
    discharge_destination = False
    arrival_mode = False
    if not pd.isna(raw.get("discharge_destination_id")):
        discharge_destination = DischargeDestination.by_id(str(raw.get("discharge_destination_id")))
        
        # Create coding for discharge destination
        coding_discharge = Coding(
        system = discharge_destination.system,
        code = discharge_destination.code,
        display = discharge_destination.display)
        
        # Create CodeableConcept for discharge destination
        code_discharge = CodeableConcept(coding= [coding_discharge])
        discharge_destination = True

    if not pd.isna(raw.get("arrival_mode_id")):
        arrival_mode = ArrivalMode.by_id(str(raw.get("arrival_mode_id")))
        
    
        # Create coding for arrival mode
        coding_arrival = Coding(
        system = arrival_mode.system,
        code = arrival_mode.code,
        display = arrival_mode.display)
        
        # Create CodeableConcept for arrival mode
        code_arrival = CodeableConcept(coding= [coding_arrival])
        arrival_mode = True
    

    if discharge_destination and arrival_mode:
        encounter.admission = EncounterAdmission(admitSource=code_arrival, dischargeDisposition=code_discharge)
    elif not arrival_mode and discharge_destination :
        encounter.admission = EncounterAdmission(dischargeDisposition=code_discharge)
    elif not discharge_destination and arrival_mode: 
        encounter.admission = EncounterAdmission(admitSource=code_arrival)
    else:
        pass
    

        # Create extensions for hospitalized_in, first_hospital, discharge_facility_department and post_acute_care
    extension_list = []
    if not pd.isna(raw.get("hospitalized_in_id")):

        hospitalized_in = HospitalizedIn.by_id(str(raw.get("hospitalized_in_id")))
        # Create hospitalized_in extension
        
        coding_hospitalized_in = Coding(
        system = hospitalized_in.system,
        code = hospitalized_in.code,
        display = hospitalized_in.display)
        
        extensionCode = CodeableConcept(coding= [coding_hospitalized_in])
        
        # Create extension url 
        extension_list.append(Extension(url ="http://testSK.org/StructureDefinition/initial-care-intensity-ext",valueCodeableConcept = extensionCode))
    
    if raw.get("first_hospital"):
        
        extension_list.append(Extension(url = "http://testSK.org/StructureDefinition/first-hospital-ext", valueBoolean = True))
    
    if not pd.isna(raw.get("discharge_facility_department_id")):
        discharge_facility_department = DischargeFacilityDepartment.by_id(str(raw.get("discharge_facility_department_id")))
        
        coding_discharge_department = Coding(
            system = discharge_facility_department.system,
            code = discharge_facility_department.code,
            display = discharge_facility_department.display
        )
        
        code_discharge_department = CodeableConcept(coding= [coding_discharge_department])
        
        extension_list.append(Extension(url = "http://testSK.org/StructureDefinition/discharge-department-service-ext", valueCodeableConcept = code_discharge_department))

    if raw.get("post_acute_care"):
        
        extension_list.append(Extension(url = "http://testSK.org/StructureDefinition/required-post-acute-care-ext", valueBoolean = True))

    encounter.extension = extension_list

    # Set the class of the encounter to inpatient
    coding_class = Coding(
        system = "http://terminology.hl7.org/CodeSystem/v3-ActCode",
        code = "IMP",
        display = "inpatient encounter"
    )
    
    code_class = CodeableConcept(coding=[coding_class])
    
    encounter.class_fhir = [code_class]
     
    # Set the period of the encounter using hospital_timestamp
    if not pd.isna(raw.get("hospital_timestamp")) and not pd.isna(raw.get("discharge_date")):
        encounter.actualPeriod = Period(start=parse_datetime(str(raw["hospital_timestamp"])), end=parse_datetime(str(raw["discharge_date"])))

    if pd.isna(raw.get("hospital_timestamp")) and not pd.isna(raw.get("discharge_date")):
        encounter.actualPeriod = Period(end=parse_datetime(str(raw["discharge_date"])))

    if pd.isna(raw.get("discharge_date")) and not pd.isna(raw.get("hospital_timestamp")):
        encounter.actualPeriod = Period(start=parse_datetime(str(raw["hospital_timestamp"])))

    
    return encounter

def build_timing_specific_observation(raw: dict, patient_ref : str, encounter_ref : str, procedure: str, thrombolisys = False, thrombectomy = False) -> Observation:
    final_observation = Observation(code=CodeableConcept(), status="final")
    final_observation.subject = Reference(reference=patient_ref)
    final_observation.encounter = Reference(reference=encounter_ref)
    final_observation.partOf = [Reference(reference=procedure)]
    final_observation.meta = {"profile": ["http://testSK.org/StructureDefinition/timing-metric-observation-profile"]}
    category_coding = Coding(
        system = "http://terminology.hl7.org/CodeSystem/observation-category",
        code = "procedure",
        display = "Procedure"
    )
    category_code = CodeableConcept(coding=[category_coding])
    final_observation.category = [category_code]

    if thrombolisys: 
        value = raw.get("door_to_needle")
        if value is None:
            raise ValueError("door_to_needle is required for thrombolisys")
        timing_obj = TimingMetricCodes.DOOR_TO_NEEDLE
        timing_value = abs(int(value))
    elif thrombectomy:
        value = raw.get("door_to_groin")
        if value is None:
            raise ValueError("door_to_groin is required for thrombectomy")
        timing_obj = TimingMetricCodes.DOOR_TO_GROIN
        timing_value = abs(int(value))


    timing_obj_coding = Coding(
        system = timing_obj.system,
        code = timing_obj.code,
        display = timing_obj.display
    )
    timing_obj_code = CodeableConcept(coding=[timing_obj_coding])
    final_observation.code = timing_obj_code
    final_observation.valueQuantity={
            "value": timing_value,
            "unit": UnitofMeasurement.MINUTE.display,
            "system": UnitofMeasurement.MINUTE.system,
            "code": UnitofMeasurement.MINUTE.code
        }

    return final_observation

def build_observation_age(age,patient_ref,encounter_ref):
    obs = Observation(code=CodeableConcept(coding=[Coding(system="http://snomed.info/sct", code="445518008" ,display ="Age at onset of clinical finding (observable entity)")]), status="final", valueInteger=int(age))
    obs.subject = Reference(reference=patient_ref)
    obs.encounter = Reference(reference=encounter_ref)

    return obs

def build_before_onset_medicationStatement_profile(raw: dict, patient_ref : str, encounter_ref : str) :
    med_taken, med_not_taken, med_unknown = get_before_onset_medications(raw)
    final_medication_lists = []
    grouped = [("Taking", med_taken), ("Not Taking", med_not_taken), ("Unknown",med_unknown)]

    for status_key, meds in grouped:
        adherence_code = AdherenceCodes.by_id(status_key)

        adherence_coding = Coding(
            system = adherence_code.system,
            code = adherence_code.code,
            display= adherence_code.display
        )
        adherence_codeable = CodeableConcept(coding=[adherence_coding])

        for bom in meds:
            coding_bom = Coding(
                system = bom.system,
                code = bom.code,
                display = bom.display
            )

            code_bom = CodeableConcept(coding=[coding_bom])
            code_med_bom = CodeableReference(concept=code_bom)


            medication_statement = MedicationStatement(
                status="recorded",
                subject=Reference(reference=patient_ref),
                medication=code_med_bom,
                encounter=Reference(reference=encounter_ref),
                adherence= MedicationStatementAdherence(code=adherence_codeable),
                meta = {"profile": ["http://testSK.org/StructureDefinition/prior-medication-statement-profile"]}
            )
            final_medication_lists.append(medication_statement)
    
    return final_medication_lists

def build_before_onset_medicationRequest_profile(raw: dict, patient_ref : str, encounter_ref : str) :
    on_discharge_meds = get_on_discharge_medications(raw)
    final_medication_lists = []
    category_coding = Coding(
        system = "http://terminology.hl7.org/CodeSystem/medicationrequest-admin-location",
        code="community",
        display="Community"
    )
    category_code = CodeableConcept(coding=[category_coding])


    for odm in on_discharge_meds:
            coding_bom = Coding(
                system = odm.system,
                code = odm.code,
                display = odm.display
            )

            code_bom = CodeableConcept(coding=[coding_bom])
            code_med_bom = CodeableReference(concept=code_bom)


            medication_statement = MedicationRequest(
                status="active",
                intent = "order",
                category = [category_code],
                subject=Reference(reference=patient_ref),
                encounter=Reference(reference=encounter_ref),
                medication=code_med_bom,
                meta = {"profile": ["http://testSK.org/StructureDefinition/discharge-medication-request-profile"]}
            )
            final_medication_lists.append(medication_statement)
    
    return final_medication_lists



def get_org_id(hospital_name: str):
    if hospital_name is None or hospital_name.strip() == "":
        raise ValueError("Hospital name is required to map to organization ID")
    if hospital_name not in provider_mapping:
        raise ValueError(f"Hospital name '{hospital_name}' not found in provider mapping")
    return provider_mapping.get(hospital_name)

def build_organization(raw : dict) -> Organization:
    org = Organization()
    org.active = True

    mapped_org_id = get_org_id(str(raw['hospital_name']))

    valueConceptOrg = Identifier(
        system="https://stroke.qualityregistry.org",
        value= str(mapped_org_id)
    )

    org.identifier = [valueConceptOrg]
    org.name = str(raw['hospital_name'])
    return org



def transform_to_fhir(raw: dict) -> Bundle:
    # 1. Patient & Encounter
    print(raw)
    patient_ref = get_uuid()
    encounter_ref = get_uuid()

    organization = build_organization(raw)
    entries = [{"fullUrl": get_uuid(), "resource": organization, "request": BundleEntryRequest(method="POST", url="Organization")}]

    patient = build_Patient(raw)
    entries.append({"fullUrl": patient_ref, "resource": patient, "request": BundleEntryRequest(method="POST", url="Patient")})

    encounter = build_stroke_encounter_profile(raw, patient_ref)
    entries.append({"fullUrl": encounter_ref, "resource": encounter, "request": BundleEntryRequest(method="POST", url="Encounter")})

    # 3. Stroke Condition
    condition_stroke_ref = None
    if raw.get("stroke_type_id"):
        condition_stroke_ref = get_uuid()
        condition_stroke = build_stroke_diagnosis_condition_profile(raw, patient_ref, encounter_ref)
        entries.append({"fullUrl": condition_stroke_ref, "resource": condition_stroke, "request": BundleEntryRequest(method="POST", url="Condition")})

    # # 4. Risk factor Conditions
    for condition in build_risk_factor_condition_profile(raw, patient_ref, encounter_ref):
        entries.append({"fullUrl": get_uuid(), "resource": condition, "request": BundleEntryRequest(method="POST", url="Condition")})

    # 5. Vital signs (now reads either field naming)
    if not safe_isna(raw.get("systolic_pressure")) or not safe_isna(raw.get("diastolic_pressure")):
        entries.append({"fullUrl": get_uuid(), "resource": build_observation_vital_signs(raw, patient_ref, encounter_ref),
                        "request": BundleEntryRequest(method="POST", url="Observation")})

    # 6. Observation: mRS (if exists)
    if not safe_isna(raw.get("prestroke_mrs")):
        observation_mrs = build_observation_mrs(raw, patient_ref, encounter_ref, prestroke=True)
        entries.append({"fullUrl": get_uuid(), "resource": observation_mrs, "request": BundleEntryRequest(method="POST", url="Observation")})

    if not safe_isna(raw.get("discharge_mrs")):
        observation_mrs = build_observation_mrs(raw, patient_ref, encounter_ref, discharge=True)
        entries.append({"fullUrl": get_uuid(), "resource": observation_mrs, "request": BundleEntryRequest(method="POST", url="Observation")})

    if not safe_isna(raw.get("three_m_mrs")):
        observation_mrs = build_observation_mrs(raw, patient_ref, encounter_ref, threem=True)
        entries.append({"fullUrl": get_uuid(), "resource": observation_mrs, "request": BundleEntryRequest(method="POST", url="Observation")})

    # 7. Observation: NIHSS (if exists)
    if not safe_isna(raw.get("nihss_score")):
        nihss_pre = build_observation_nihss(raw, patient_ref, encounter_ref, admission=True)
        entries.append({"fullUrl": get_uuid(), "resource": nihss_pre, "request": BundleEntryRequest(method="POST", url="Observation")})

    if not safe_isna(raw.get("discharge_nihss_score")):
        nihss_adm = build_observation_nihss(raw, patient_ref, encounter_ref, discharge=True)
        entries.append({"fullUrl": get_uuid(), "resource": nihss_adm, "request": BundleEntryRequest(method="POST", url="Observation")})

    # 8. Observation: Mtici Score (if exists)
    if not safe_isna(raw.get("mtici_score")):
        observation_mtici_score = build_observation_mtici_score(raw, patient_ref, encounter_ref)
        entries.append({"fullUrl": get_uuid(), "resource": observation_mtici_score, "request": BundleEntryRequest(method="POST", url="Observation")})

    if not safe_isna(raw.get("age")):
        observation_age = build_observation_age(raw.get("age"), patient_ref, encounter_ref)
        entries.append({"fullUrl": get_uuid(), "resource": observation_age, "request": BundleEntryRequest(method="POST", url="Observation")})

    if not safe_isna(raw.get("carotid_arteries_imaging")):
        procedure_carotid = build_carotid_imaging_procedure(raw, patient_ref, encounter_ref, raw.get("carotid_arteries_imaging"))
        entries.append({"fullUrl": get_uuid(), "resource": procedure_carotid, "request": BundleEntryRequest(method="POST", url="Procedure")})

    if not safe_isna(raw.get("risk_smoker_last_10_years")):
        obs = build_observation_smoking(raw, patient_ref, encounter_ref)
        entries.append({"fullUrl": get_uuid(), "resource": obs, "request": BundleEntryRequest(method="POST", url="Observation")})


    if not safe_isna(raw.get("wake_up_stroke")):
        ensure_dependency(condition_stroke_ref is not None,
                          need="Stroke Condition",
                          because="wake_up_stroke=true needs a Condition to reference")
        obs = build_stroke_circumstance_observation(patient_ref, encounter_ref, condition_stroke_ref, wake_up=True)
        entries.append({"fullUrl": get_uuid(), "resource": obs, "request": BundleEntryRequest(method="POST", url="Observation")})

    if not safe_isna(raw.get("in_hospital_stroke")):
        ensure_dependency(condition_stroke_ref is not None,
                          need="Stroke Condition",
                          because="in_hospital_stroke=true needs a Condition to reference")
        obs = build_stroke_circumstance_observation(patient_ref, encounter_ref, condition_stroke_ref, in_hosp=True)
        entries.append({"fullUrl": get_uuid(), "resource": obs, "request": BundleEntryRequest(method="POST", url="Observation")})

    # Imaging procedure requires identifiers when you call it (función ya valida internamente)
    if not safe_isna(raw.get("imaging_type_id")) and not safe_isna(raw.get("imaging_done_id")):
        proc_img = build_imaging_procedure(raw, patient_ref, encounter_ref)
        entries.append({"fullUrl": get_uuid(), "resource": proc_img, "request": BundleEntryRequest(method="POST", url="Procedure")})

    # Thrombolysis
    if raw.get("thrombolisys") or not safe_isna(raw.get("no_thrombolisys_reason_id")):
        proc_thrombolysis_ref = get_uuid()
        proc_thrombolysis = build_thrombolysis_procedure(raw, patient_ref, encounter_ref)
        entries.append({"fullUrl": proc_thrombolysis_ref, "resource": proc_thrombolysis, "request": BundleEntryRequest(method="POST", url="Procedure")})
        if not safe_isna(raw.get("door_to_needle")):
            obs = build_timing_specific_observation(raw, patient_ref, encounter_ref, proc_thrombolysis_ref, thrombolisys=True)
            entries.append({"fullUrl": get_uuid(), "resource": obs, "request": BundleEntryRequest(method="POST", url="Observation")})

    # Thrombectomy (requires Stroke Condition ref for complications link)
    if raw.get("thrombectomy") or not safe_isna(raw.get("no_thrombectomy_reason_id")):
        ensure_dependency(condition_stroke_ref is not None,
                          need="Stroke Condition",
                          because="thrombectomy/complications need to reference the Condition")
        proc_thrombectomy_ref = get_uuid()
        proc_thrombectomy = build_thrombectomy_procedure(raw, patient_ref, encounter_ref, condition_stroke_ref)
        entries.append({"fullUrl": proc_thrombectomy_ref, "resource": proc_thrombectomy, "request": BundleEntryRequest(method="POST", url="Procedure")})
        if not safe_isna(raw.get("door_to_groin")):
            obs = build_timing_specific_observation(raw, patient_ref, encounter_ref, proc_thrombectomy_ref, thrombectomy=True)
            entries.append({"fullUrl": get_uuid(), "resource": obs, "request": BundleEntryRequest(method="POST", url="Observation")})

    if not safe_isna(raw.get("swallowing_screening_type_id")):
        proc_swallowing = build_swallowing_screening_procedure(raw, patient_ref, encounter_ref)
        entries.append({"fullUrl": get_uuid(), "resource": proc_swallowing, "request": BundleEntryRequest(method="POST", url="Procedure")})

    # AF/Flutter (required id validated inside builder)
    if not safe_isna(raw.get("atrial_fibrillation_or_flutter_id")):
        entries.append({"fullUrl": get_uuid(),
                        "resource": build_observation_Af_or_F(raw, patient_ref, encounter_ref),
                        "request": BundleEntryRequest(method="POST", url="Observation")})

    # Before-onset meds
    for med_statement in build_before_onset_medicationStatement_profile(raw, patient_ref, encounter_ref):
        entries.append({"fullUrl": get_uuid(), "resource": med_statement, "request": BundleEntryRequest(method="POST", url="MedicationStatement")})
    
    for med_request in build_before_onset_medicationRequest_profile(raw, patient_ref, encounter_ref):
        entries.append({"fullUrl": get_uuid(), "resource": med_request, "request": BundleEntryRequest(method="POST", url="MedicationRequest")})


    bundle_final = Bundle(type="transaction")
    bundle_final.entry = entries
    return bundle_final

