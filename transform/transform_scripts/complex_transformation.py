import json
from pyspark.sql.functions import substring, col, when
from pyspark.sql import functions as F
import pandas as pd
from custom_functions import mapping
from direct_mapping import (
    atrial_fibrillation_or_flutter_map,
    no_thrombolysis_reason_map,
    no_thrombectomy_reason_map
)
import shm_variables as shm

from enum_models import (
    ImagingType,
    MTiciScore,
    AtrialFibrillationOrFlutter,
    ProcedureNotDoneReason
)


def one_column_to_multiple_columns(dictionary, dataframe, source_column):
    for target_column, values in dictionary.items():
        print(target_column, values)
        dataframe = dataframe.withColumn(
            target_column,
            when(col(source_column).isin(values), True)
            .when(col(source_column).isNotNull(), False)
            .otherwise(None))
        print(dataframe.select(F.col(target_column)).show())
    return dataframe


def process_mrs(dataframe, mrs_column: str):
    """
    mRS columns are columns with any string. Therefore we are processing the
    mRS column to get the last character of the string that usually represents
    the mRS score. If the value is 'exitus' then the value is 6. However, we are
    not able to process the mRS value if the last character is not a number or
    number is on different position. In this case, we are setting the value to None.
    """
    mrs_values = ['0', '1', '2', '3', '4', '5', '6']
    if mrs_column not in dataframe.columns:
        return dataframe
    # create a new column with the last character of the mrs column
    dataframe = dataframe.withColumn(
        f"{mrs_column}_lastchar", substring(col(mrs_column), -1, 1))
    return dataframe.withColumn(
        mrs_column,
        #when(col(mrs_column) == 'exitus', int('6'))  # if the value is 'exitus' then the value is 6
        when(
            (col(mrs_column).isNotNull()) & (col(f"{mrs_column}_lastchar").isin(mrs_values)),
            col(f"{mrs_column}_lastchar").cast('int'))  # if the value is not null and the last character is in mrs_values then cast it to int
        .otherwise(None)
    )


def no_thrombolysis_reason(dataframe):
    # mapping function transform column values based on the mapping dictionary
    dataframe = mapping(dataframe, source_col= shm.thrombolysis, target_col=shm.no_thrombolysis_reason, lookup=no_thrombolysis_reason_map)
    print(dataframe.select(col(shm.no_thrombolysis_reason)).show())
    return dataframe.withColumn(
        shm.no_thrombolysis_reason,
        when(col("no_ivt_reason_time_window") == '1', ProcedureNotDoneReason.TIME_WINDOW.id)
        .when(col("no_ivt_reason_mild_deficit") == '1', ProcedureNotDoneReason.MILD_DEFICIT.id)
        .otherwise(col(shm.no_thrombolysis_reason)))


def no_thrombectomy_reason(dataframe):
    # mapping function transform column values based on the mapping dictionary
    dataframe = mapping(dataframe, source_col= shm.thrombectomy, target_col=shm.no_thrombectomy_reason, lookup=no_thrombectomy_reason_map)
    return dataframe.withColumn(
        shm.no_thrombectomy_reason,
        when(col("no_mt_reason_time_window") == '1', ProcedureNotDoneReason.TIME_WINDOW.id)
        .when(col("no_mt_reason_mild_deficit") == '1', ProcedureNotDoneReason.MILD_DEFICIT.id)
        .when(col("no_mt_reason_premorbidity") == '1', ProcedureNotDoneReason.DISABILITY.id)
        .otherwise(col(shm.no_thrombectomy_reason)))


def imaging_types(dataframe):
    return dataframe.withColumn(
        shm.imaging_type,
        when(
            (col("ct_perfusion") == '1') & (col(shm.imaging_type) == '1'),
            ((ImagingType.CT_CTA_PERFUSION.id)))
        .when(
            (col("ct_perfusion") == '1') & (col(shm.imaging_type) == '3'),
            ((ImagingType.MR_MRA_PERFUSION.id)))
        .when(
            (col("ct_angio") == '1') & (col(shm.imaging_type) == '1'),
            (ImagingType.CT_CTA.id))
        .when(
            (col("ct_angio") == '1') & (col(shm.imaging_type) == '3'),
            (ImagingType.MR_MRA.id))
        .when(col(shm.imaging_type) == '1', ((ImagingType.CT.id)))
        .when(col(shm.imaging_type) == '3', ((ImagingType.MR.id)))
        .otherwise(None))


def reperfusion_timestamp(dataframe):
    return dataframe.withColumn(
        shm.reperfusion_timestamp,
        when(col(shm.mtici_score) == MTiciScore.ZERO.id, None)
        .otherwise(col(shm.reperfusion_timestamp)))


def transform_atrial_fibrillaton(dataframe):
    # mapping function transform column values based on the mapping dictionary
    dataframe = mapping(
        dataframe, shm.atrial_fibrillation_or_flutter, atrial_fibrillation_or_flutter_map)
    return dataframe.withColumn(
        shm.atrial_fibrillation_or_flutter,
        when(
            (col(shm.risk_atrial_fibrillation) == True),
            ((AtrialFibrillationOrFlutter.KNOWN_AF.id)))
        .otherwise(col(shm.atrial_fibrillation_or_flutter))
        )


def transformation_post_acute_care(dataframe):
    """
        SK registry dont collect post acute care, however RES-Q defines
        post-acute care as hospitalization more then 24 hours after admission.
        Therefore, we can calculate post acute care by calculating the difference
        between admission and discharge date. If the difference is more then 1 day
        then the patient was hospitalized more then 24 hours.
        if difference is less then 1 day then the patient was hospitalized less then 24 hours.
        But if the difference is exactly 1 day then we can't determine if the patient was hospitalized
        more or less then 24 hours. In this case we are setting the value to None.
    """


    df = dataframe.withColumn("hospital_timestamp", F.to_timestamp("hospital_timestamp")).withColumn("discharge_date", F.to_timestamp("discharge_date"))
    # Calculamos la diferencia en días (float)
    diff = F.datediff(F.col("discharge_date"), F.col("hospital_timestamp"))


    df = df.withColumn(
            "post_acute_care",
            F.when(diff > 1, F.lit(True))
            .when(diff < 1, F.lit(False))
            .when(diff == 1, F.lit(None))  # indeterminado
            .otherwise(F.lit(None))
        )

    return df


def transform_bleeding_reason(dataframe):
    bleeding = {
        shm.bleeding_reason_aneurysm: ['2'],  # 2=aneurysm
        shm.bleeding_reason_malformation: ['3', '5'],  # 3=tumour, 5=malformation
        shm.bleeding_reason_other: ['1', '4', '6', '8'],
        # 1=spontaneous, 4=into IS source, 6=vascuis, 8=other
    }
    # when single SK registry contains multiple values for bleeding reason
    # we need to transform it to multiple RES-Q columns with boolean values
    # one_column_to_multiple_columns function is used for this transformation
    # see definition of such function in the beginning of this file
    return one_column_to_multiple_columns(bleeding, dataframe, "bleeding_reasons")


def transform_etiology(dataframe):
    etiologies = {
        shm.stroke_etiology_cardioembolism: ['1'],
        shm.stroke_etiology_la_atherosclerosis: ['2'],
        shm.stroke_etiology_lacunar: ['3'],
        shm.stroke_etiology_cryptogenic_stroke: ['4'],
        shm.stroke_etiology_other: ['5'],
    }
    # when single SK registry contains multiple values for bleeding reason
    # we need to transform it to multiple RES-Q columns with boolean values
    # one_column_to_multiple_columns function is used for this transformation
    # see definition of such function in the beginning of this file
    return one_column_to_multiple_columns(
        etiologies, dataframe, "etiology")


def transform_before_onset_anticoagulants(dataframe):
    anticoagulants = {
        shm.before_onset_warfarin: ['1'],
        "before_onset_doak": ['6'],
        shm.before_onset_other_anticoagulant: ['98'],
    }
    # when single SK registry contains multiple values for bleeding reason
    # we need to transform it to multiple RES-Q columns with boolean values
    # one_column_to_multiple_columns function is used for this transformation
    # see definition of such function in the beginning of this file
    return one_column_to_multiple_columns(
        anticoagulants, dataframe, "before_onset_anticoagulants")
