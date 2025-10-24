from enum_models import (
    BeforeOnsetMedication,
    ProcedureNotDoneReason,
    Sex,
        ArrivalMode,
            ImagingDone,
                StrokeType,
                    AtrialFibrillationOrFlutter,
                                SwallowingScreeningDone,
                                    SwallowingScreeningTiming,
                                        DischargeDestination,
                                            HospitalizedIn,
                                                MTiciScore,
                                                    SwallowingScreeningType,
                                                        DischargeFacilityDepartment,
                                                        BleedingReason,
                                                        StrokeEtiology,
                                                        Bool
)

sex_map = {
    '1': Sex.MALE.id,
    '2': Sex.FEMALE.id,
    '3': Sex.OTHER.id
}

arrival_mode_map = {
    '1': ArrivalMode.EMS_HOME.id,
    '2': ArrivalMode.PRIVATE_TRANSPORTATION_HOME.id,
    '3': ArrivalMode.STROKE_CENTER.id,
    '4': ArrivalMode.ANOTHER_HOSPITAL.id,
    '5': ArrivalMode.EMS_GP.id,
    '6': ArrivalMode.PRIVATE_TRANSPORTATION_GP.id
}

first_hospital_map = {
    '1': True,
    '2': True,
    '3': False,
    '4': True,
    '5': False,
}

hospitalized_in_map = {
    '1': HospitalizedIn.ICU_STROKE_UNIT.id,
    '2': HospitalizedIn.MONITORED.id,
    '3': HospitalizedIn.STANDARD.id,
}

inhospital_map = {
    '1': False,
    '2': False,
    '3': False,
    '4': True,
    '5': None,
}

imaging_done_map = {
    '2': ImagingDone.ELSEWHERE.id,
    '4': ImagingDone.ELSEWHERE.id,
    '5': ImagingDone.NO.id,
    '1': ImagingDone.YES.id,
    '3': ImagingDone.YES.id,
}

before_onset_anticoagulant_map = {
    '1': BeforeOnsetMedication.WARFARIN.id,
    '6': BeforeOnsetMedication.ANTICOAGULANT.id,
    '98': BeforeOnsetMedication.ANTICOAGULANT.id,
}


stroke_type_map = {
    '1': StrokeType.SUBARACHNOID_HEMORRHAGE.id,
    '2': StrokeType.INTRACEREBRAL_HEMORRHAGE.id,
    '3': StrokeType.INTRACEREBRAL_HEMORRHAGE.id,
    '4': StrokeType.TRANSIENT_ISCHEMIC.id,
    '5': StrokeType.ISCHEMIC.id,
    '6': StrokeType.UNDETERMINED.id
}

stroke_etiology_map = {
    '1': StrokeEtiology.CARDIOEMBOLYSM.id,
    '2': StrokeEtiology.ATHEROSCLEROSIS.id,
    '3': StrokeEtiology.LACUNAR.id,
    '4': StrokeEtiology.CRYPTOGENIC_STROKE.id,
    '5': StrokeEtiology.OTHER.id

}

bleeding_reason_map = {
    '2': BleedingReason.ANEURYSM.id,
    '3': BleedingReason.MALFORMATION.id,
    '1': BleedingReason.OTHER.id,
    '4': BleedingReason.OTHER.id,
    '5': BleedingReason.MALFORMATION.id,
    '6': BleedingReason.OTHER.id,
    '8': BleedingReason.OTHER.id

}
atrial_fibrillation_or_flutter_map = {
    '1': AtrialFibrillationOrFlutter.KNOWN_AF.id,
    '2': AtrialFibrillationOrFlutter.NO_AF.id,
}

no_thrombolysis_reason_map = {
    '2': ProcedureNotDoneReason.DONE_ELSEWHERE.id,
    '3': ProcedureNotDoneReason.TRANSFERRED_ELSEWHERE.id,
}

no_thrombectomy_reason_map = {
    
    '2': ProcedureNotDoneReason.DONE_ELSEWHERE.id,
    '3': ProcedureNotDoneReason.TRANSFERRED_ELSEWHERE.id,
}

swallowing_screening_done_map = {
    '1': SwallowingScreeningDone.YES.id,
    '2': SwallowingScreeningDone.YES.id,
    '3': SwallowingScreeningDone.NO.id,
}

swallowing_screening_timing_map = {
    '1': SwallowingScreeningTiming.WITHIN_24_HOURS.id,
    '2': SwallowingScreeningTiming.AFTER_24_HOURS.id
}

swallowing_screening_type_map = {
    '1': SwallowingScreeningType.GUSS.id,
    '2': SwallowingScreeningType.WATER_TEST.id,
    '3': SwallowingScreeningType.OTHER.id,
    '4': SwallowingScreeningType.OTHER.id,
    '5': SwallowingScreeningType.OTHER.id,
    '6': SwallowingScreeningType.OTHER.id,
}

discharge_destination_map = {
    '1': DischargeDestination.HOME.id,
    '3': DischargeDestination.ANOTHER_HOSPITAL.id,
    '2': DischargeDestination.SOCIAL_CARE.id,
    '4': DischargeDestination.DEAD.id
}

discharge_facility_department_map = {
    '1': DischargeFacilityDepartment.ACUTE_REHABILITATION.id,
    '2': DischargeFacilityDepartment.POSTCARE_BED.id,
    '4': DischargeFacilityDepartment.NEUROLOGY.id,
    '9': DischargeFacilityDepartment.ANOTHER_DEPARTMENT.id,
}

mtici_score_map = {
    '00': MTiciScore.ZERO.id,
    '000': MTiciScore.ZERO.id,
    '10': MTiciScore.ONE.id,
    '010': MTiciScore.ONE.id,
    '2a': MTiciScore.TWO_A.id,
    '02a': MTiciScore.TWO_A.id,
    '2b': MTiciScore.TWO_B.id,
    '02b': MTiciScore.TWO_B.id,
    '30': MTiciScore.THREE.id,
    '030': MTiciScore.THREE.id,
}

smoker_map = {
    '3': True,
    '6': False,
    '8': True,
    '9': True,
}

bool_map = {
    '1': True,
    '2': False,
    '3': False,
}
