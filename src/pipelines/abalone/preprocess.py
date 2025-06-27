"""Feature engineers the dataset."""
import logging
import joblib
import numpy as np
import pandas as pd

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder

# from tokenizers import BertWordPieceTokenizer

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

def remove_outliers(group, col="price"):
    q1 = group[col].quantile(0.25)
    q3 = group[col].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return group[(group[col] >= lower) & (group[col] <= upper)]

def feat_engineer_hist(df):

    return df


def feat_engineer_timebased(df):

    df_copy = df.copy()

    # remove outliers based on price per type_id and is_buy_order
    df_copy = (df_copy.groupby(["type_id", "is_buy_order"], group_keys=False)
               .apply(remove_outliers, col="price"))
    
    # get the grouped datas aggregated minimum sell and maximum buy price for each reference_timestamp
    # TODO: add the system id as well
    df_step_one = (df_copy
                    .groupby(["reference_timestamp", "type_id", "is_buy_order"], group_keys=False)
                    .agg(
                        min_sell_price=pd.NamedAgg(column="price", aggfunc="min"),
                        max_buy_price=pd.NamedAgg(column="price", aggfunc="max"),)
                    .reset_index()
            )

    # based on the reference timestamp, get the last 5 entries for each type_id and is_buy_order
    df_step_two = (df_step_one
                    .sort_values(by=["reference_timestamp"])
                    .groupby(["type_id", "is_buy_order"])
                    .shift(periods=[1,2,3,4,5], suffix="_prev"))

    timebased_features = pd.concat([df_step_one, df_step_two], axis=1)
    return timebased_features


def crerate_train_df(df):
    # select a subset of columns for training and ensure the target column is present and in the first position
    # SageMaker XGBoost has the convention of target in the first column
    df = df[[
        "max_buy_price", # Target
        "type_id", 
        "is_buy_order", 
        "min_sell_price_prev_1",
        "max_buy_price_prev_1",
        "min_sell_price_prev_2",
        "max_buy_price_prev_2",
        "min_sell_price_prev_3",
        "max_buy_price_prev_3",
        "min_sell_price_prev_4",
        "max_buy_price_prev_4",
        "min_sell_price_prev_5",
        "max_buy_price_prev_5",
    ]]

    return df
             

# class EmbeddingTransformer(BaseEstimator, TransformerMixin):
#     def __init__(self, string_features, max_length=5, vocab_size=20):
#         self.max_length = max_length
#         self.vocab_size = vocab_size
#         self.tokenizer = BertWordPieceTokenizer()
#         self.string_features = string_features
#         self.is_fitted_ = False

#     def fit(self, X, y=None):
#         unique_values = pd.unique(X[self.string_features].astype(str).values.flatten()).tolist()
#         self.tokenizer.train_from_iterator(
#             unique_values,
#             vocab_size=self.vocab_size,
#             min_frequency=1,
#             special_tokens=[
#                 "[PAD]",
#                 "[CLS]",
#                 "[SEP]",
#                 "[UNK]",
#                 "[MASK]",
#             ],
#         )
#         self.is_fitted_ = True
#         return self

#     def transform(self, X, column=None):
#         if not self.is_fitted_:
#             raise RuntimeError("The transformer has not been fitted yet.")
#         # Use the provided column or default to self.string_features
#         result = []
        
#         if column is None:
#             col = self.string_features
#         else:
#             col = column if isinstance(column, list) else [column]

#         for c in col:
#             values = X[c].astype(str).values
#             encoded = [self.tokenizer.encode(str(x)) for x in values]
#             padded = np.zeros((len(encoded), self.max_length), dtype=int)
#             for i, seq in enumerate(encoded):
#                 padded[i, :min(len(seq.ids), self.max_length)] = seq.ids[:self.max_length]
                
#             df = pd.DataFrame(padded, columns=[f"{c}_token_{i}" for i in range(self.max_length)])
#             result.append(df)
#         # Concatenate all token columns horizontally
#         return pd.concat(result, axis=1)
    
    
def fit_pipeline(df, numeric_features, base_dir):
    # numeric_transformer = make_pipeline(
    #                     SimpleImputer(strategy='mean'),
    #                     StandardScaler())
    
    categorical_features = ["is_buy_order"]

    categorical_transformer = make_pipeline(
                        OneHotEncoder())
    
    # string_features = ["type_id"]
    
    # embedding_transformer = make_pipeline(
    #                     EmbeddingTransformer(string_features, max_length=5, vocab_size=20))

    preprocess = ColumnTransformer(
        transformers=[
            # ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
            # ("embed", embedding_transformer, string_features),
        ])


    preprocess.fit(df)
    joblib.dump(preprocess, f"{base_dir}/encoder/model.joblib")
    
    return preprocess


def main():
    logger.debug("Starting preprocessing.")

    base_dir = "/opt/ml/processing"

    logger.debug("Reading downloaded data.")
    df = pd.read_parquet(f"{base_dir}/input/data")

    df["reference_timestamp"] = df["year"].astype(str) + "-" + df["month"].astype(str) + "-" + df["day"].astype(str) + " " + df["hour"].astype(str)
    df["reference_timestamp"] = pd.to_datetime(df["reference_timestamp"], format="%Y-%m-%d %H")

    df = feat_engineer_hist(df)

    df_timebased = feat_engineer_timebased(df)
    # merge it back to the original dataframe
    df = pd.merge(df, df_timebased, on=["type_id", "reference_timestamp","is_buy_order"], how="left")
    
    df = crerate_train_df(df)
    df = df.dropna()

    logger.debug("Defining transformers.")
        
    numeric_features = []

    logger.info("Splitting %d rows of data into train, validation, test datasets.", len(df))
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    train, validation, test = np.split(df, [int(0.7 * len(df)), int(0.85 * len(df))])

    logger.info("Fitting transformers on train dataset with %d rows.", len(train))
    preprocess = fit_pipeline(df, numeric_features, base_dir)   
    logger.info("Applying transforms.")
   
    y = train.pop("max_buy_price")
    X_train = preprocess.transform(train)
    y_train = y.to_numpy().reshape(len(y), 1)
    train = np.concatenate((X_train, y_train), axis=1)

    pd.DataFrame(train).to_csv(
        f"{base_dir}/train/train.csv", header=False, index=False)

    y = validation.pop("max_buy_price")
    X_validation = preprocess.transform(validation)
    y_validation = y.to_numpy().reshape(len(y), 1)
    validation = np.concatenate((X_validation, y_validation), axis=1)
    pd.DataFrame(validation).to_csv(
        f"{base_dir}/validation/validation.csv", header=False, index=False)
    
    y = test.pop("max_buy_price")
    X_test = preprocess.transform(test)
    y_test = y.to_numpy().reshape(len(y), 1)
    test = np.concatenate((X_test, y_test), axis=1)
    pd.DataFrame(test).to_csv(
        f"{base_dir}/test/test.csv", header=False, index=False)


if __name__ == "__main__":
    main()