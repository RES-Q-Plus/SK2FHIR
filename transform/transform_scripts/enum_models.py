from enum import Enum, unique
import json
from fhir.resources.coding import Coding

class ConceptEnum(Enum):
    """
    Base generic for enums whose values are dicts
    with the keys 'code', 'display', and 'system'.
    Provides .code, .display, .system, and .to_coding().
    """
    id: str
    code: str
    display: str
    system: str

    def __new__(cls, id: str, value: dict):
        obj = object.__new__(cls)
        obj._value_ = value      # <-- aquí vive el dict
        obj.id = id
        obj.code    = value["code"]
        obj.display = value["display"]
        obj.system  = value["system"]
        
        return obj
    @classmethod
    def by_id(cls, id_str: str):
        """Returns the Enum member whose .id == id_str."""
        for m in cls:
            if m.id == id_str:
                return m
        raise KeyError(f"{cls.__name__}: id not found -> {id_str}")
    
    @classmethod
    def dict_by_id(cls, id_str: str) -> dict:
        """Returns the dict (not serialized) associated with the id."""
        return cls.by_id(id_str).value
    
    @classmethod
    def json_by_id(cls, id_str: str) -> str:
        """Returns the JSON (string) associated with the id."""
        return json.dumps(cls.dict_by_id(id_str), ensure_ascii=False)

    def to_coding(self) -> Coding:
        """Build and return a fhir.resources.Coding."""
        coding = Coding(
        system = self.system,
        code = self.code,
        display = self.display)
        return coding

class Sex(ConceptEnum):
    MALE   = ("Male", {"code" : "248153007", "display": "Male (finding)", "system": "http://snomed.info/sct"})
    FEMALE = ("Female", {"code" : "248152002", "display": "Female (finding)", "system": "http://snomed.info/sct"})
    OTHER  = ("Other", {"code" : "32570681000036106", "display": "Indeterminate sex (finding)", "system": "http://snomed.info/sct"})


class ArrivalMode(ConceptEnum):
    EMS_GP = ("Emergency Medical Services", {"code": "ems-gp", "display": "EMS from GP", "system": "http://testSK.org/CodeSystem/stroke-arrival-mode-cs"})
    PRIVATE_TRANSPORTATION_HOME = ("Private Transportation Home", {"code": "priv-transport-home", "display": "Private Transportation from Home/Scene", "system": "http://testSK.org/CodeSystem/stroke-arrival-mode-cs"})
    PRIVATE_TRANSPORTATION_GP = ("Private Transportation GP", {"code": "priv-transport-gp", "display": "Private Transportation from GP", "system": "http://testSK.org/CodeSystem/stroke-arrival-mode-cs"})
    STROKE_CENTER = ("Stroke Center", {"code": "stroke-center", "display": "Stroke Center", "system": "http://testSK.org/CodeSystem/stroke-arrival-mode-cs"})
    EMS_HOME = ("Emergency Medical Services", {"code": "ems-home", "display": "EMS from Home", "system": "http://testSK.org/CodeSystem/stroke-arrival-mode-cs"})
    ANOTHER_HOSPITAL = ("Another Hospital", {"code": "another-hosp", "display": "Another Hospital", "system": "http://testSK.org/CodeSystem/stroke-arrival-mode-cs"})


class FirstHospital(ConceptEnum):
    TRUE = ("True", {"code": "true", "display": "True", "system": "http://testSK.org/StructureDefinition/first-hospital-ext"})
    FALSE = ("False", {"code": "false", "display": "False", "system": "http://testSK.org/StructureDefinition/first-hospital-ext"})


class HospitalizedIn(ConceptEnum):
    ICU_STROKE_UNIT = ("ICU Stroke Unit", {"code": "icu-stroke", "display": "ICU / Stroke Unit", "system": "http://testSK.org/CodeSystem/initial-care-intensity-cs"})
    STANDARD = ("Standard", {"code": "standard", "display": "Standard Bed", "system": "http://testSK.org/CodeSystem/initial-care-intensity-cs"})
    MONITORED = ("Monitored", {"code": "monitored", "display": "Monitored Bed", "system": "http://testSK.org/CodeSystem/initial-care-intensity-cs"})

class ImagingDone(ConceptEnum):
    YES = ("Yes", {"code": "yes", "display": "Yes", "system": ""})
    NO = ("No", {"code": "no", "display": "No", "system": ""})
    ELSEWHERE = ("Elsewhere", {"code": "elsewhere", "display": "Elsewhere", "system": ""})


class InHospital(ConceptEnum):
    FALSE = ("False", {"code": "false", "display": "False", "system": "http://hl7.org/fhir/in-hospital"})
    TRUE = ("True", {"code": "true", "display": "True", "system": "http://hl7.org/fhir/in-hospital"})
    NONE = ("None", {"code": "none", "display": "None", "system": "http://hl7.org/fhir/in-hospital"})

class ImagingType(ConceptEnum):
    MR_MRA_PERFUSION = ("MR MRA Perfusion", {"code": "mr-dwi-flair-mra-perfusion", "display": "MR DWI-FLAIR, MRA, and Perfusion", "system": "http://testSK.org/CodeSystem/brain-imaging-type-cs"})
    CT_CTA_PERFUSION = ("CT CTA Perfusion", {"code": "ct-cta-perfusion", "display": "CT-CTA and Perfusion", "system": "http://testSK.org/CodeSystem/brain-imaging-type-cs"})
    CT_CTA = ("CT CTA", {"code": "ct-cta", "display": "Computed Tomography (CT) and CT Angiography (CTA)", "system": "http://testSK.org/CodeSystem/brain-imaging-type-cs"})
    MR_MRA = ("MR MRA", {"code": "mr-dwi-flair-mra", "display": "MR MRA", "system": "http://testSK.org/CodeSystem/brain-imaging-type-cs"})
    CT = ("CT", {"code": "396205005", "display": "Computed tomography of brain without radiopaque contrast (procedure)", "system": "http://snomed.info/sct"})
    MR = ("MR", {"code": "mr-dwi-flair", "display": "MR", "system": "http://testSK.org/CodeSystem/brain-imaging-type-cs"})
    
class StrokeType(ConceptEnum):
    INTRACEREBRAL_HEMORRHAGE = ("Intracerebral Hemorrhage", {"code": "274100004", "display": "Cerebral hemorrhage (disorder)", "system": "http://snomed.info/sct"})
    SUBARACHNOID_HEMORRHAGE  = ("Subarachnoid Hemorrhage", {"code": "21454007", "display": "Subarachnoid intracranial hemorrhage (disorder)", "system": "http://snomed.info/sct"})
    ISCHEMIC                = ("Ischemic", {"code": "422504002", "display": "Ischemic stroke (disorder)", "system": "http://snomed.info/sct"})
    TRANSIENT_ISCHEMIC      = ("Transient Ischemic", {"code": "266257000", "display": "Transient ischemic attack (disorder)", "system": "http://snomed.info/sct"})
    CEREBRAL_VENOUS_THROMBOSIS = ("Cerebral Venous Thrombosis", {"code": "95455008", "display": "Thrombosis of cerebral veins (disorder)", "system": "http://snomed.info/sct"})
    STROKE_MIMICS = ("Stroke Mimics", {"code": "230690007", "display": "Cerebrovascular accident (disorder)", "system": "http://snomed.info/sct"})
    UNDETERMINED            = ("Undetermined", {"code": "230690007", "display": "Cerebrovascular accident (disorder)", "system": "http://snomed.info/sct"})

class StrokeEtiology(ConceptEnum):
        CARDIOEMBOLYSM = ("Cardioembolism", {"code": "413758000", "display": "Cardioembolic stroke (disorder)", "system": "http://snomed.info/sct"})
        ATHEROSCLEROSIS = ("Atherosclerosis", {"code": "atherosclerosis", "display": "Stroke Etiology Atherosclerosis", "system": "http://testSK.org/CodeSystem/stroke-etiology-cs"})
        LACUNAR = ("Lacunar", {"code": "lacunar", "display": "Stroke Etiology Lacunar", "system": "http://testSK.org/CodeSystem/stroke-etiology-cs"})
        CRYPTOGENIC_STROKE = ("Cryptogenic Stroke", {"code": "16891111000119104", "display": "Cryptogenic stroke (disorder)", "system": "http://snomed.info/sct"})
        OTHER= ("Other", {"code": "other", "display": "Stroke Etiology Other", "system": "http://testSK.org/CodeSystem/stroke-etiology-cs"})

class BleedingReason(ConceptEnum):
    ANEURYSM = ("Aneurysm", {"code": "aneurysm", "display": "Bleeding Reason Aneurysm", "system": "http://testSK.org/CodeSystem/hemorrhagic-stroke-bleeding-reason-cs"})
    MALFORMATION = ("Malformation", {"code": "malformation", "display": "Bleeding Reason Malformation", "system": "http://testSK.org/CodeSystem/hemorrhagic-stroke-bleeding-reason-cs"})
    OTHER = ("Other", {"code": "other", "display": "Bleeding Reason Other", "system": "http://testSK.org/CodeSystem/hemorrhagic-stroke-bleeding-reason-cs"})

class AtrialFibrillationOrFlutter(ConceptEnum):
    KNOWN_AF = ("Known AF", {"code": "410515005", "display": "Known present (qualifier value)", "system": "http://snomed.info/sct"})
    NO_AF = ("No AF", {"code": "410516002", "display": "Known absent (qualifier value)", "system": "http://snomed.info/sct"})
    NOT_SCREENED = ("Not Screened", {"code": "261665006", "display": "Unknown (qualifier value)", "system": "http://snomed.info/sct"})
    DETECTED = ("Detected", {"code": "410515003", "display": "Known present (qualifier value)", "system": "http://snomed.info/sct"})

class BeforeOnsetMedication(ConceptEnum):
    ANTIHYPERTENSIVE = ("Antihypertensive", {"code": "308116003", "display": "Antihypertensive therapy (procedure)", "system": "http://snomed.info/sct"})
    ANTICOAGULANT = ("Anticoagulant", {"code": "182764009", "display": "Anticoagulant therapy (procedure)", "system": "http://snomed.info/sct"})
    CONTRACEPTION = ("Contraception", {"code": "1237404009", "display": "Uses hormone method of contraception (finding)", "system": "http://snomed.info/sct"})
    STATIN = ("Statin", {"code": "315053001", "display": "Administration of prophylactic statin (procedure)", "system": "http://snomed.info/sct"})
    WARFARIN = ("Warfarin", {"code": "722045009", "display": "Warfarin therapy (procedure)", "system": "http://snomed.info/sct"})
    OTHER_ANTICOAGULANT = ("Other Anticoagulant", {"code": "other-anticoagulant", "display": "Other Anticoagulant", "system": "http://testSK.org/CodeSystem/medication-statement-cs"})
    ANTIDIABETIC = ("Antidiabetic", {"code": "antidiabetic", "display": "Any Antidiabetic", "system": "http://testSK.org/CodeSystem/medication-statement-cs"})
    ANTIPLATELET = ("Antiplatelet", {"code": "antiplatelet", "display": "Any Antiplatelet", "system": "http://testSK.org/CodeSystem/medication-statement-cs"})
    ASA = ("ASA", {"code": "asa", "display": "Aspirin", "system": "http://testSK.org/CodeSystem/medication-statement-cs"})
    CLOPIDOGREL = ("Clopidogrel", {"code": "clopidogrel", "display": "Clopidogrel", "system": "http://testSK.org/CodeSystem/medication-statement-cs"})


class ProcedureNotDoneReason(ConceptEnum):
    DONE_ELSEWHERE = ("Done Elsewhere", {"code": "done-elsewhere", "display": "Performed Elsewhere", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    TRANSFERRED_ELSEWHERE = ("Transferred Elsewhere", {"code": "transfer", "display": "Transferred to Another Facility", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    TIME_WINDOW = ("Time Window", {"code": "time-window", "display": "Outside Therapeutic Window", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    MILD_DEFICIT = ("Mild Deficit", {"code": "mild-deficit", "display": "Mild Deficit", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    DISABILITY = ("Disability", {"code": "disability", "display": "Disability", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})  
    COST = ("Cost", {"code": "cost", "display": "Cost / No Insurance", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    NOT_AVAILABLE = ("Not Available", {"code": "unavailable", "display": "Not Available", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    OTHER = ("Other", {"code": "other", "display": "Other Reason", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    NO_LARGE_VESSEL = ("No Large Vessel", {"code": "no-lvo", "display": "No Large Vessel Occlusion (LVO)", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    CONSENT = ("Consent", {"code": "consent", "display": "Consent Not Obtained", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    TECHNICALLY_NOT_POSSIBLE = ("Technically Not Possible", {"code": "technically-not-possible", "display": "Technically Not Possible", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    NO_ANGIOGRAPHY = ("No Angiography", {"code": "no-angiography", "display": "Angiography Not Performed", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    ONLY_MT = ("Only MT", {"code": "only-mt", "display": "Only Mechanical Thrombectomy Considered", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    NO_LVO = ("No LVO", {"code": "no-lvo", "display": "No Large Vessel Occlusion (LVO)", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    CONTRAINDICATION = ("Contraindication", {"code": "contraindication", "display": "Contraindication Present", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    PATIENT_REFUSAL = ("Patient Refusal", {"code": "patient-refusal", "display": "Patient/Family Refusal", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})
    UNKNOWN = ("Unknown", {"code": "unknown", "display": "Unknown Reason", "system": "http://testSK.org/CodeSystem/stroke-proc-not-done-reason-cs"})

class SwallowingScreeningDone(ConceptEnum):
    YES = ("Yes", {"code": "385658003", "display": "Done (qualifier value)", "system": "http://snomed.info/sct"})
    NO = ("No", {"code": "385660001", "display": "Not done (qualifier value)", "system": "http://snomed.info/sct"})
    NOT_APPLICABLE = ("Not Applicable", {"code": "385432009", "display": "Not applicable (qualifier value)", "system": "http://snomed.info/sct"})

class SwallowingScreeningTiming(ConceptEnum):
    WITHIN_24_HOURS = ("Within 24 Hours", {"code": "281380002", "display": "24 hours post admission (qualifier value)", "system": "http://snomed.info/sct"})
    AFTER_24_HOURS = ("After 24 Hours", {"code": "281381003", "display": "More than 24 hours after admission (qualifier value)", "system": "http://snomed.info/sct"})
    WITHIN_4_HOURS = ("Within 4 Hours", {"code": "T4H", "display": "Within 4 Hours", "system": "http://testSK.org/CodeSystem/swallow-screen-time-cs"})

class SwallowingScreeningType(ConceptEnum):
    GUSS = ("GUSS", {"code": "1290000005", "display": "Assessment using Gugging Swallowing Screen (procedure)", "system": "http://snomed.info/sct"})
    WATER_TEST = ("Water Test", {"code": "63913004", "display": "Tonography with water provocation (procedure)", "system": "http://snomed.info/sct"})
    OTHER = ("Other", {"code": "other", "display": "Other Swallow Procedure", "system": "http://testSK.org/CodeSystem/swallow-procedures-cs"})
    ASSIST = ("Assist", {"code": "assist", "display": "ASSIST", "system": "http://testSK.org/CodeSystem/swallow-procedures-cs"})
    VST = ("VST", {"code": "v-vst", "display": "V-VST", "system": "http://testSK.org/CodeSystem/swallow-procedures-cs"})

class DischargeDestination(ConceptEnum):
    HOME = ("Home", {"code": "306689006", "display": "Discharge to home (procedure)", "system": "http://snomed.info/sct"})
    ANOTHER_HOSPITAL = ("Another Hospital", {"code": "19712007", "display": "Patient transfer, to another health care facility (procedure)", "system": "http://snomed.info/sct"})
    SAME_HOSPITAL = ("Same Hospital", {"code": "37729005", "display": "Patient transfer, in-hospital (procedure)", "system": "http://snomed.info/sct"})
    SOCIAL_CARE = ("Social Care", {"code": "306694006", "display": "Discharge to nursing home (procedure)", "system": "http://snomed.info/sct"})
    DEAD = ("Dead", {"code": "dead", "display": "Patient Deceased", "system": "http://testSK.org/CodeSystem/stroke-discharge-destination-cs"})

class DischargeFacilityDepartment(ConceptEnum):
    ACUTE_REHABILITATION = ("Acute Rehabilitation", {"code": "acute", "display": "Acute Rehabilitation", "system": "http://testSK.org/CodeSystem/CodeSystem/discharge-dept-cs"})
    POSTCARE_BED = ("Postcare Bed", {"code": "post-care", "display": "Post Care Bed", "system": "http://testSK.org/CodeSystem/CodeSystem/discharge-dept-cs"})
    NEUROLOGY = ("Neurology", {"code": "neurology", "display": "Neurology", "system": "http://testSK.org/CodeSystem/CodeSystem/discharge-dept-cs"})
    ANOTHER_DEPARTMENT = ("Another Department", {"code": "another-department", "display": "Another Department", "system": "http://testSK.org/CodeSystem/CodeSystem/discharge-dept-cs"})


class MTiciScore(ConceptEnum):
    ZERO   = ("Zero", {"code": "0", "display": "Grade 0: No perfusion", "system": "http://testSK.org/CodeSystem/mtici-score-cs"})
    ONE    = ("One", {"code": "1", "display": "Grade 1: Antegrade reperfusion past the initial occlusion, but limited distal branch filling with little or slow distal reperfusion", "system": "http://testSK.org/CodeSystem/mtici-score-cs"})
    TWO_A  = ("Two A", {"code": "2a", "display": "Grade 2a: Antegrade reperfusion of less than half of the occluded target artery previously ischemic territory", "system": "http://testSK.org/CodeSystem/mtici-score-cs"})
    TWO_B  = ("Two B", {"code": "2b", "display": "Grade 2b: Antegrade reperfusion of more than half of the previously occluded target artery ischemic territory", "system": "http://testSK.org/CodeSystem/mtici-score-cs"})
    TWO_C  = ("Two C", {"code": "2c", "display": "Grade 2c: Near complete perfusion except for slow flow or distal emboli in a few distal cortical vessels", "system": "http://testSK.org/CodeSystem/mtici-score-cs"})
    THREE  = ("Three", {"code": "3", "display": "Grade 3: Complete antegrade reperfusion of the previously occluded target artery ischemic territory, with absence of visualized occlusion in all distal branches", "system": "http://testSK.org/CodeSystem/mtici-score-cs"})

class RiskFactor(ConceptEnum):
    AtrialFibrillation = ("AtrialFibrillation", {"code": "49436004", "display": "Atrial fibrillation (disorder)", "system": "http://snomed.info/sct"})
    AtrialFlutter = ("AtrialFlutter", {"code": "5370000", "display": "Atrial flutter (disorder)", "system": "http://snomed.info/sct"})
    CoronaryArteryDisease = ("CoronaryArteryDisease", {"code": "53741008", "display": "Coronary arteriosclerosis (disorder)", "system": "http://snomed.info/sct"})
    Hypertension = ("Hypertension", {"code": "38341003", "display": "Hypertensive disorder, systemic arterial (disorder)", "system": "http://snomed.info/sct"})
    Diabetes = ("Diabetes", {"code": "73211009", "display": "Diabetes mellitus (disorder)", "system": "http://snomed.info/sct"})
    Hyperlipidemia = ("Hyperlipidemia", {"code": "55822004", "display": "Hyperlipidemia (disorder)", "system": "http://snomed.info/sct"})
    PreviousHemorrahagicStroke = ("PreviousHemorraghicStroke", {"code": "230706003", "display": "Hemorrhagic cerebral infarction (disorder)", "system": "http://snomed.info/sct"})
    PreviousIschemicStroke = ("PreviousIschemicStroke", {"code": "266257000", "display": "Transient ischemic attack (disorder)", "system": "http://snomed.info/sct"})
    PreviousStroke = ("PreviousStroke", {"code": "230690007", "display": "Cerebrovascular accident (disorder)", "system": "http://snomed.info/sct"})
    Smoker = ("Smoker", {"code": "77176002", "display": "Smoker (finding)", "system": "http://snomed.info/sct"})

class Bool(ConceptEnum):
    TRUE = ("True", {"code": "true", "display": "True", "system": "http://hl7.org/fhir/bool"})
    FALSE = ("False", {"code": "false", "display": "False", "system": "http://hl7.org/fhir/bool"})

class DischargeMedication(ConceptEnum):
    ANTIPLATELET = ("Antiplatelet", {"code": "antiplatelet", "display": "Any Antiplatelet", "system": "http://testSK.org/CodeSystem/discharge-medication-cs"})
    ANTICOAGULANT = ("Anticoagulant", {"code": "anticoagulant", "display": "Any Anticoagulant", "system": "http://testSK.org/CodeSystem/discharge-medication-cs"})
    ASPIRIN = ("Aspirin", {"code": "asa", "display": "Aspirin", "system": "http://testSK.org/CodeSystem/discharge-medication-cs"})
    HEPARIN = ("Heparin", {"code": "heparin", "display": "Heparin", "system": "http://testSK.org/CodeSystem/discharge-medication-cs"})
    WARFARIN = ("Warfarin", {"code": "warfarin", "display": "Warfarin", "system": "http://testSK.org/CodeSystem/discharge-medication-cs"})
    STATIN = ("Statin", {"code": "statin", "display": "Statin", "system": "http://testSK.org/CodeSystem/discharge-medication-cs"})
    ANTIDIABETIC = ("Antidiabetic", {"code": "antidiabetics", "display": "Antidiabetics", "system": "http://testSK.org/CodeSystem/discharge-medication-cs"})
    ANTIHYPERTENSIVE = ("Antihypertensive", {"code": "antihypertensive", "display": "Antihypertensive", "system": "http://testSK.org/CodeSystem/discharge-medication-cs"})
    OTHER_ANTIPLATELET = ("Other Antiplatelet", {"code": "other-antiplatelet", "display": "Other Antiplatelet", "system": "http://testSK.org/CodeSystem/discharge-medication-cs"})
    CLOPIDOGREL = ("Clopidogrel", {"code": "clopidogrel", "display": "Clopidogrel", "system": "http://testSK.org/CodeSystem/discharge-medication-cs"})
    CONTRACEPTION = ("Contraception", {"code": "contraception", "display": "Contraception", "system": "http://testSK.org/CodeSystem/discharge-medication-cs"})
    OTHER = ("Other", {"code": "other", "display": "Other", "system": "http://testSK.org/CodeSystem/discharge-medication-cs"})

class VitalSigns(ConceptEnum):
    SYSTOLIC = ("Systolic", {"code": "271649006", "display": "Systolic blood pressure (observable entity)", "system": "http://snomed.info/sct"})
    DIASTOLIC = ("Diastolic", {"code": "271650006", "display": "Diastolic blood pressure (observable entity)", "system": "http://snomed.info/sct"})
    TAKE_VS = ("Take VS", {"code": "61746007", "display": "Taking patient vital signs (procedure)", "system": "http://snomed.info/sct"})

class MRsScore(ConceptEnum):
    ZERO   = ("0", {"code": "0", "display": "No symptoms at all", "system": "http://testSK.org/CodeSystem/mrs-score-cs"})
    ONE    = ("1", {"code": "1", "display": "No significant disability despite symptoms; able to carry out all usual duties and activities", "system": "http://testSK.org/CodeSystem/mrs-score-cs"})
    TWO    = ("2", {"code": "2", "display": "Slight disability; unable to carry out all previous activities, but able to look after own affairs without assistance", "system": "http://testSK.org/CodeSystem/mrs-score-cs"})
    THREE  = ("3", {"code": "3", "display": "Moderate disability; requiring some help, but able to walk without assistance", "system": "http://testSK.org/CodeSystem/mrs-score-cs"})
    FOUR   = ("4", {"code": "4", "display": "Moderately severe disability; unable to walk without assistance and unable to attend to own bodily needs without assistance", "system": "http://testSK.org/CodeSystem/mrs-score-cs"})
    FIVE   = ("5", {"code": "5", "display": "Severe disability; bedridden, incontinent and requiring constant nursing care and attention", "system": "http://testSK.org/CodeSystem/mrs-score-cs"})
    SIX    = ("6", {"code": "6", "display": "Dead", "system": "http://testSK.org/CodeSystem/mrs-score-cs"})

class FunctionalScore(ConceptEnum):
    MRS = ("MRS", {"code": "1255866005", "display": "Modified Rankin Scale score (observable entity)", "system": "http://snomed.info/sct"})
    NIHSS = ("NIHSS", {"code": "450743008", "display": "National Institutes of Health stroke scale score (observable entity)", "system": "http://snomed.info/sct"})

class AssessmentContext(ConceptEnum):
    PRESTROKE = ("Prestroke", {"code": "pre-stroke", "display": "Pre-stroke", "system": "http://testSK.org/CodeSystem/assessment-context-cs"})
    DISCHARGE = ("Discharge", {"code": "discharge", "display": "Discharge", "system": "http://testSK.org/CodeSystem/assessment-context-cs"})
    THREE_MONTHS = ("Three Months", {"code": "3-month", "display": "3 Month Follow-up", "system": "http://testSK.org/CodeSystem/assessment-context-cs"})
    ADMISSION = ("Admission", {"code": "admission", "display": "Admission", "system": "http://testSK.org/CodeSystem/assessment-context-cs"})

class SpecificFinding(ConceptEnum):
    MTICI = ("MTICI", {"code": "mTICI", "display": "mTICI", "system": "http://testSK.org/CodeSystem/mtici-code-cs"})
    
class CarotidImaging(ConceptEnum):
    CAROTID = ("Carotid", {"code": "58920005", "display": "Angiography of carotid artery (procedure)", "system": "http://snomed.info/sct"})

class StrokeCircumstance(ConceptEnum):
    WAKE_UP = ("Wake Up", {"code": "wake-up", "display": "Wake Up Stroke", "system": "http://testSK.org/CodeSystem/stroke-circumstance-codes-cs"})
    IN_HOSPITAL = ("In Hospital", {"code": "in-hospital", "display": "In Hospital Stroke", "system": "http://testSK.org/CodeSystem/stroke-circumstance-codes-cs"})

class PostAcuteCare(ConceptEnum):
    TRUE = ("True", {"code": "post-acute", "display": "Acute Phase (<24h)", "system": "http://testSK.org/CodeSystem/procedure-timing-context-cs"})
    FALSE = ("False", {"code": "acute", "display": "Post-Acute Phase (>=24h)", "system": "http://testSK.org/CodeSystem/procedure-timing-context-cs"})
    NONE = ("None", {"code": "unknown", "display": "Unknown/Not Applicable", "system": "http://testSK.org/CodeSystem/procedure-timing-context-cs"})

class PerforationProcedures(ConceptEnum):
    THROMBOLYSIS = ("Thrombolysis", {"code": "472191000119101", "display": "Thrombolysis of cerebral artery by intravenous infusion (procedure)", "system": "http://snomed.info/sct"})
    THROMBECTOMY = ("Thrombectomy", {"code": "397046001", "display": "Thrombectomy of artery (procedure)", "system": "http://snomed.info/sct"})

class TimingMetricCodes(ConceptEnum):
    DOOR_TO_GROIN = ("Door2Groin", {"code": "D2G", "display": "Door to Groin", "system": "http://testSK.org/CodeSystem/timing-metric-codes-cs"})
    DOOR_TO_NEEDLE = ("Door2Needle", {"code": "D2N", "display": "Door to Needle", "system": "http://testSK.org/CodeSystem/timing-metric-codes-cs"})

class ThrombectomyComplications(ConceptEnum):
    PERFORATION = ("Perforation", {"code": "307312008", "display": "Perforation of artery (disorder)", "system": "http://snomed.info/sct"})

class UnitofMeasurement(ConceptEnum):
    MINUTE = ("Minute", {"code": "min", "display": "minute", "system": "https://ucum.org/ucum"})
    MMGM = ("mmHg", {"code": "mm[Hg]", "display": "millimeter Mercury column", "system": "https://ucum.org/ucum"})

class AdherenceCodes(ConceptEnum):
    TAKING = ("Taking", {"code":"taking", "display": "Taking", "system": "http://hl7.org/fhir/CodeSystem/medication-statement-adherence"})
    NOT_TAKING = ("Not Taking", {"code":"not-taking", "display": "Not Taking", "system": "http://hl7.org/fhir/CodeSystem/medication-statement-adherence"})
    UNKNOWN = ("Unknown", {"code": "unknown", "display": "Unknown", "system": "http://hl7.org/fhir/CodeSystem/medication-statement-adherence"})

class ClinicalStatusCodes(ConceptEnum):
    ACTIVE = ("Active", {"code":"active", "display": "Active", "system": "http://terminology.hl7.org/CodeSystem/condition-clinical"})
    INACTIVE = ("Inactive", {"code":"inactive", "display": "Inactive", "system": "http://terminology.hl7.org/CodeSystem/condition-clinical"})
    REMISSION = ("Remission", {"code":"remission", "display": "Remission", "system": "http://terminology.hl7.org/CodeSystem/condition-clinical"})
    UNKNOWN = ("Unknown", {"code": "unknown", "display": "Unknown", "system": "http://terminology.hl7.org/CodeSystem/condition-clinical"})

    