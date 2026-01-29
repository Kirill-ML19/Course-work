import pandas as pd

def build(df:pd.DataFrame, parsed_result:pd.Series)->pd.DataFrame:
    '''
    This function collects a DataFrame of target variables.

    Parametrs:
        df (pd.DataFrame): original dataframe.
        parsed_result (pd.Series): one-dimensional table of target variables.

    Returns:
        df_final (pd.Dataframe): A dataframe with target variables converted to float32 and structured columns.
    '''
    columns = [result['big_five'] for result in parsed_result]
    big_five_df = pd.DataFrame(columns)
    big_five_df = big_five_df.drop(columns=big_five_df.columns[-1])
    if bool(big_five_df.any().any()):
        big_five_df=big_five_df = big_five_df.dropna(axis=0, how='any', subset=big_five_df.columns[big_five_df.isna().any()].tolist())
    df_final = pd.concat([df[['vk_id','completion_date']], big_five_df], axis=1)
    df_final = df_final.sort_values('completion_date').groupby('vk_id').last().reset_index()
    df_final = df_final.drop(columns='completion_date')
    return df_final