"""Feature engineers the dataset."""
import logging
import joblib
import numpy as np
import pandas as pd

# import common.embedding_transformer as embedding_transformer

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder

from tokenizers import BertWordPieceTokenizer

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


class EmbeddingTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, string_features, max_length=5, vocab_size=20):
        self.max_length = max_length
        self.vocab_size = vocab_size
        self.tokenizer = BertWordPieceTokenizer()
        self.string_features = string_features
        self.is_fitted_ = False

    def fit(self, X, y=None):
        unique_values = pd.unique(X[self.string_features].astype(str).values.flatten()).tolist()
        self.tokenizer.train_from_iterator(
            unique_values,
            vocab_size=self.vocab_size,
            min_frequency=1,
            special_tokens=[
                "[PAD]",
                "[CLS]",
                "[SEP]",
                "[UNK]",
                "[MASK]",
            ],
        )
        self.is_fitted_ = True
        return self

    def transform(self, X, column=None):
        if not self.is_fitted_:
            raise RuntimeError("The transformer has not been fitted yet.")
        # Use the provided column or default to self.string_features
        result = []
        
        if column is None:
            col = self.string_features
        else:
            col = column if isinstance(column, list) else [column]

        for c in col:
            values = X[c].astype(str).values
            encoded = [self.tokenizer.encode(str(x)) for x in values]
            padded = np.zeros((len(encoded), self.max_length), dtype=int)
            for i, seq in enumerate(encoded):
                padded[i, :min(len(seq.ids), self.max_length)] = seq.ids[:self.max_length]
                
            df = pd.DataFrame(padded, columns=[f"{c}_token_{i}" for i in range(self.max_length)])
            result.append(df)
        # Concatenate all token columns horizontally
        return pd.concat(result, axis=1)


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


def create_train_df(df):
    # select a subset of columns for training and ensure the target column is nolonger present 
    df_out = df[[
        "max_buy_price",
        "reference_timestamp",
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

    return df_out


def load_encoder(base_dir):
    """Load the encoder from the specified directory."""
    try:
        encoder = joblib.load(f"{base_dir}/encoder/model.joblib")
        logger.info("Encoder loaded successfully.")
        return encoder
    except FileNotFoundError:
        logger.error("Encoder model not found. Please ensure it has been created and saved correctly.")
        raise
    except Exception as e:
        logger.error(f"An error occurred while loading the encoder: {e}")
        raise


def main(base_dir="/opt/ml/processing"):
    logger.debug("Starting preprocessing.")

    logger.debug("Reading downloaded data.")
    df = pd.read_parquet(f"{base_dir}/input/data")

    df["reference_timestamp"] = df["year"].astype(str) + "-" + df["month"].astype(str) + "-" + df["day"].astype(str) + " " + df["hour"].astype(str)
    df["reference_timestamp"] = pd.to_datetime(df["reference_timestamp"], format="%Y-%m-%d %H")

    df = feat_engineer_hist(df)

    df_timebased = feat_engineer_timebased(df)
    # merge it back to the original dataframe
    df = pd.merge(df, df_timebased, on=["type_id", "reference_timestamp","is_buy_order"], how="left")
          
    logger.info("Splitting %d rows of data into train, validation, test datasets.", len(df))
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
       
    logger.info("Reduce down the features then creating train, validation, test datasets.")
    df_subset = create_train_df(df)
    df_subset = df_subset.dropna()

    logger.info("Loading  encoder from file")
    preprocess = load_encoder(base_dir)     
    
    # Get the latest reference_timestamp from the dataframe and only consider buy orders?
    latest_timestamp = df_subset["reference_timestamp"].max()
    df_subset = df_subset[df_subset["reference_timestamp"] == latest_timestamp]
    df_subset = df_subset.drop(columns=["reference_timestamp"])

    X = preprocess.transform(df_subset)
    pd.DataFrame(X).to_csv(
        f"{base_dir}/transform/data.csv", header=False, index=False)

if __name__ == "__main__":
    main()