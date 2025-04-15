"""Feature engineers the abalone dataset."""
import argparse
import logging
import os
import pathlib
import requests
import tempfile

import boto3
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OrdinalEncoder

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

if __name__ == "__main__":
    logger.debug("Starting preprocessing.")

    base_dir = "/opt/ml/processing"

    logger.debug("Reading downloaded data.")
    df = pd.read_parquet("/opt/ml/processing/input/data")

    df.drop_duplicates(subset=["processed_timestamp","type_id"], inplace=True)
    df["prev_price"] = df.groupby("type_id").shift(1)["average_price"]

    date_time = pd.to_datetime(df.pop('processed_timestamp'), format='%Y-%m-%d %H:%M:%S').drop_duplicates()

    feature_columns_dtype = {
        "adjusted_price": np.float64,
        "average_price": np.float64,
        "type_id": str,
        "hour": np.float64,
        "month": str,
        "day" : str,
    }

    df = df.astype(feature_columns_dtype)
    
    logger.debug("Defining transformers.")
        
    numeric_features = [
        "prev_price",
        ]

    numeric_transformer = Pipeline(
            steps=[("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler())]
        )
    
    categorical_features = ["type_id"]

    categorical_transformer = Pipeline(
    steps=[
        ("imputer", SimpleImputer(strategy="constant")),
        ("onehot", OrdinalEncoder()),
    ]
)

    preprocess = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    logger.info("Applying transforms.")
    y = df.pop("average_price")
    X_pre = preprocess.fit_transform(df)
    y_pre = y.to_numpy().reshape(len(y), 1)

    X = np.concatenate((y_pre, X_pre), axis=1)

    logger.info("Splitting %d rows of data into train, validation, test datasets.", len(X))
    np.random.shuffle(X)
    train, validation, test = np.split(X, [int(0.7 * len(X)), int(0.85 * len(X))])

    logger.info("Writing out datasets to %s.", base_dir)
    pd.DataFrame(train).to_csv(f"{base_dir}/train/train.csv", header=False, index=False)
    pd.DataFrame(validation).to_csv(
        f"{base_dir}/validation/validation.csv", header=False, index=False
    )
    pd.DataFrame(test).to_csv(f"{base_dir}/test/test.csv", header=False, index=False)
