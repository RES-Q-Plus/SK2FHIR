from library import rename_dataframe_columns, to_timestamp, to_time
from custom_functions import (
    mapping,
    minute_difference,
    cast_types,
    remove_values,
    disjuction
)
import direct_mapping as maps
import shm_variables as shm
from rename_columns import column_mapping
import complex_transformation as cetl


def transformation(input_dataframe):
    df = to_timestamp(input_dataframe, shm.onset_date, "M/d/yyyy H:mm")
    df = to_timestamp(df, shm.onset_time, "M/d/yyyy H:mm")
    df = to_timestamp(df, shm.discharge_date, "M/d/yyyy H:mm")
    df = to_timestamp(df, shm.hospital_timestamp, "M/d/yyyy H:mm")
    df = to_timestamp(df, shm.imaging_timestamp, "M/d/yyyy H:mm")
    df = to_timestamp(df, shm.bolus_timestamp,"M/d/yyyy H:mm")
    df = to_timestamp(df, shm.puncture_timestamp,"M/d/yyyy H:mm")
    df = to_timestamp(df, shm.reperfusion_timestamp,"M/d/yyyy H:mm")

    df = minute_difference(df, shm.door_to_needle, shm.bolus_timestamp, shm.hospital_timestamp)
    df = minute_difference(df, shm.door_to_groin, shm.puncture_timestamp, shm.hospital_timestamp)

    df = cast_types(df, 'int', int_columns)

    for column in str_to_bool_columns:
        df = mapping(df, column, maps.bool_map)

    df = disjuction(df, shm.risk_previous_ischemic_stroke, [
         shm.risk_previous_ischemic_stroke,
         'risk_tia'])
    df = disjuction(df, shm.risk_previous_stroke, [
         shm.risk_previous_ischemic_stroke,
         shm.risk_previous_hemorrhagic_stroke])
    df = disjuction(df, shm.discharge_other, [
         shm.discharge_other,
        'discharge_other2'])
    df = disjuction(df, shm.before_onset_any_antiplatelet, before_onset_antiplatelet_types)
    df = disjuction(df, shm.discharge_any_antiplatelet, discharge_antiplatelet_types)
    df = disjuction(df, shm.discharge_any_anticoagulant, discharge_anticoagulant_types)
    df = mapping(df, shm.sex, maps.sex_map)
    df = mapping(df, shm.arrival_mode, maps.arrival_mode_map)
    df = mapping(df, source_col= shm.imaging_type, target_col=shm.imaging_done, lookup=maps.imaging_done_map)

    df = mapping(df, shm.stroke_type, maps.stroke_type_map)
    df = mapping(df, shm.no_thrombolysis_reason, maps.no_thrombolysis_reason_map)
    df = mapping(df, shm.no_thrombectomy_reason, maps.no_thrombectomy_reason_map)
    df = mapping(df, shm.swallowing_screening_done, maps.swallowing_screening_done_map)
    df = mapping(df, shm.swallowing_screening_type, maps.swallowing_screening_type_map)
    df = mapping(df, shm.swallowing_screening_timing, maps.swallowing_screening_timing_map)
    df = mapping(df, shm.discharge_destination, maps.discharge_destination_map)
    df = mapping(df, shm.discharge_facility_department, maps.discharge_facility_department_map)
    df = mapping(df, shm.risk_smoker_last_10_years, maps.smoker_map)
    df = mapping(df, shm.hospitalized_in, maps.hospitalized_in_map)
    df = mapping(df, shm.mtici_score, maps.mtici_score_map)
    df = mapping(df, source_col= shm.inhospital_stroke, target_col= shm.first_hospital, lookup=maps.first_hospital_map)
    df = mapping(df, shm.inhospital_stroke, maps.inhospital_map)


    
    df = remove_values(df, shm.prestroke_mrs, [range(6, 10)])
    df = remove_values(df, shm.nihss_score, [range(43, 100)])
    df = remove_values(df, shm.discharge_nihss_score, [range(43, 100)])


    df = cetl.transform_atrial_fibrillaton(df)
    df = cetl.transform_before_onset_anticoagulants(df)
    df = cetl.transform_bleeding_reason(df)
    df = cetl.transform_etiology(df)
    df = cetl.no_thrombolysis_reason(df)
    df = cetl.no_thrombectomy_reason(df)
    df = cetl.imaging_types(df)
    df = cetl.reperfusion_timestamp(df)
    df = cetl.transformation_post_acute_care(df)
    df = cetl.process_mrs(df, shm.discharge_mrs)
    df = cetl.process_mrs(df, shm.three_m_mrs)

    df = disjuction(
        df,
        shm.before_onset_any_anticoagulant,
        before_onset_anticoagulant_types)


    # Quitar columnas que no aparezcan en el fichero shm_variables.py mediante un for que las recorra
    for column in df.columns:
        if column not in shm.__dict__.values():
            df = df.drop(column)
    return df


int_columns = [
    shm.age,
    shm.systolic_pressure,
    shm.diastolic_pressure,
    shm.nihss_score,
    shm.prestroke_mrs,
    shm.door_to_needle,
    shm.door_to_groin,
    shm.discharge_nihss_score,
]

str_to_bool_columns = [
    "risk_tia",
    shm.wakeup_stroke,
    shm.risk_hyperlipidemia,
    shm.risk_previous_ischemic_stroke,
    shm.risk_previous_stroke,
    shm.risk_previous_hemorrhagic_stroke,
    shm.risk_coronary_artery_disease_or_myocardial_infarction,
    shm.risk_diabetes,
    shm.before_onset_antidiabetics,
    shm.risk_atrial_fibrillation,
    shm.risk_hypertension,
    shm.before_onset_antihypertensives,
    shm.before_onset_asa,
    shm.before_onset_clopidogrel,
    shm.before_onset_statin,
    shm.before_onset_contraception,
    shm.thrombolysis,
    shm.thrombectomy,
    shm.carotid_arteries_imaging,
    shm.discharge_asa,
    shm.discharge_clopidogrel,
    shm.discharge_warfarin,
    "discharge_doak",
    shm.discharge_heparin,
    shm.discharge_statin,
    shm.discharge_other,
    "discharge_other2",
    shm.mt_complications_perforation,
]

before_onset_anticoagulant_types = [
    shm.before_onset_warfarin,
    shm.before_onset_other_anticoagulant,
    "before_onset_doak",
]

discharge_anticoagulant_types = [
    shm.discharge_warfarin,
    shm.discharge_heparin,
    "discharge_doak",
]

discharge_antiplatelet_types = [
    shm.discharge_asa,
    shm.discharge_clopidogrel,
]

before_onset_antiplatelet_types = [
    shm.before_onset_asa,
    shm.before_onset_clopidogrel,
]