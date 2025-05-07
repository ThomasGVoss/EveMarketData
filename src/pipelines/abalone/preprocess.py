"""Feature engineers the dataset."""
import logging
import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OrdinalEncoder

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

def basic_cleanup(df):

    # Basic clean up
    df.drop_duplicates(subset=["processed_timestamp", "type_id"], inplace=True)

        # Cut the maximum price to 1.5 times the 90th percentile
    q1 = df['average_price'].quantile(0.25)
    q3 = df['average_price'].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    df.loc[df['average_price'] > upper_bound, 'average_price'] = upper_bound

    return df


def feat_engineer_hist(df):

    for n in range(1,5):
        df[f"price_t-{n}"] = df.groupby("type_id").shift(n)["average_price"]

    df["5_day_rolling_mean"] = df.groupby('type_id')['average_price'].rolling(window=5,min_periods=1).mean().reset_index(level=0, drop=True)
    df["5_day_rolling_std"] = df.groupby('type_id')['average_price'].rolling(window=5,min_periods=1).std().reset_index(level=0, drop=True)
    
    # Price changes
    df["price_change"] = df.groupby('type_id')['average_price'].diff().bfill().ffill()

    return df

def feat_engineer_timebased(df):

    df["processed_timestamp"] = pd.to_datetime(df["processed_timestamp"])
    df['day_of_week'] = df["processed_timestamp"].dt.dayofweek # 0 = Monday, 6 = Sunday# make sure not to use day_of_week - https://pandas.pydata.org/pandas-docs/version/1.5/reference/api/pandas.Series.dt.day_of_week.html
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)  # 1 if weekend, 0 otherwise
    df['month'] = df["processed_timestamp"].dt.month
    df['hour'] = df["processed_timestamp"].dt.hour

    return df


def main():
    logger.debug("Starting preprocessing.")

    base_dir = "/opt/ml/processing"

    logger.debug("Reading downloaded data.")
    df = pd.read_parquet(f"{base_dir}/input/data")

    df = basic_cleanup(df)

    df = feat_engineer_hist(df)

    df = feat_engineer_timebased(df)
    
    df = df.dropna()

    logger.debug("Defining transformers.")
        
    numeric_features = [
        "price_t-1",
        "price_t-2",
        "price_t-3",
        "price_t-4",
        "price_change",
        "5_day_rolling_mean",
        "5_day_rolling_std"
        ]

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler())
            ])
    
    categorical_features = ["is_weekend"]

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant")),
            ("onehot", OrdinalEncoder()),
        ])

    preprocess = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ])

    logger.info("Applying transforms.")
    y = df.pop("average_price")
    X_pre = preprocess.fit_transform(df)
    y_pre = y.to_numpy().reshape(len(y), 1)

    # I guess i will need this one again for the inference pipeline
    joblib.dump(preprocess, f"{base_dir}/encoder/model.joblib")

    X = np.concatenate((y_pre, X_pre), axis=1)

    logger.info("Splitting %d rows of data into train, validation, test datasets.", len(X))
    np.random.shuffle(X)
    train, validation, test = np.split(X, [int(0.7 * len(X)), int(0.85 * len(X))])

    logger.info("Writing out datasets to %s.", base_dir)
    pd.DataFrame(train).to_csv(
        f"{base_dir}/train/train.csv", header=False, index=False)
    pd.DataFrame(validation).to_csv(
        f"{base_dir}/validation/validation.csv", header=False, index=False)
    pd.DataFrame(test).to_csv(
        f"{base_dir}/test/test.csv", header=False, index=False)


if __name__ == "__main__":
    main()