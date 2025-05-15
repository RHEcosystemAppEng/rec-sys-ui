import feast
from typing import List
import numpy as np
from pydantic import BaseModel
from datetime import datetime
from typing import Literal
from feast import FeatureStore

# Load items from Parquet file
store = FeatureStore('')

class User(BaseModel):
    user_id: int
    age: int
    gender: Literal['M', 'F', 'Other']
    signup_date: datetime
    preferences: Literal['Electronics', 'Books', 'Clothing', 'Home', 'Sports']
    
#  TODO random the initiate user

def load_items_exiting_user(user_id: int) -> List[int]:
    suggested_item_ids = store.get_online_features(
        features=store.get_feature_service('user_top_k_items'),
        entity_rows=[{'user_id': user_id}]
    )
    
    top_item_ids = suggested_item_ids.to_df().iloc[0]['top_k_item_ids']
    
    suggested_item = store.get_online_features(
        features=store.get_feature_service('item_service'),
        entity_rows=[{'item_id': item_id}  for item_id in top_item_ids]
    ).to_df()
    print(suggested_item)
    return suggested_item, 0
    
# def load_items_new_user(store: feast.FeatureService):
#     num_new_user = 1
#     new_users = generate_users(num_new_user, num_users + 1)
#     new_users_embeddings = user_encoder(**data_preproccess(new_users))
#     top_k_items = []
#     for user_embed in new_users_embeddings:
#         top_k = store.retrieve_online_documents(
#             query=user_embed.tolist(),
#             top_k=k,
#             # feature=f'{item_embedding_view}:item_id'
#             features=[f'{item_embedding_view}:item_id']
#         )
#         top_k_items.append(top_k.to_df())

#     new_users['top_k_items'] = top_k_items
#     new_users[['item_id', 'top_k_items']]