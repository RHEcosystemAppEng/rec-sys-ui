import gradio as gr
import pandas as pd
from kafka import KafkaProducer
import json
from datetime import datetime
from utils import load_items_exiting_user
from feast import FeatureStore
from typing import List

# Load items from Parquet file
store = FeatureStore('')

# Kafka producer setup
kafka_service = 'rec-sys-cluster-kafka-bootstrap.rec-sys.svc.cluster.local:9092'
producer = KafkaProducer(
    bootstrap_servers=kafka_service,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def build_intercation_payload(user_id, item_id, interaction_type, rating=None, quantity=None):
    schema = {
        "type": "struct",
        "fields": [{
            "field": "user_id",
            "type": "int32",
            "optional": False,
        }, {
            "field": "item_id",
            "type": "int32",
            "optional": False,
        }, {
            "field": "timestamp",
            "type": "string",
            "optional": False,
            "format": "timestamp",
        }, {
            "field": "interaction_type",
            "type": "string",
            "optional": False,
        }, {
            "field": "rating",
            "type": "int32",
            "optional": True,
        }, {
            "field": "quantity",
            "type": "int32",
            "optional": True,
        }],
        "optional": False,
        "name": "interaction"
    }
    interaction = {
        'user_id': int(user_id),
        'item_id': int(item_id),
        'timestamp': datetime.now().isoformat(" "),
        'interaction_type': interaction_type,
        'rating': int(rating) if rating is not None else None,
        'quantity': int(quantity) if quantity is not None else None
    }
    message = {
        "schema": schema,
        "payload": interaction
    }
    return message

# Function to send interaction to Kafka
def send_interaction(message, sentiment):
    payload = message['payload']
    user_id, item_id, interaction_type = payload['user_id'], payload['item_id'], payload['interaction_type']
    if sentiment == 'positive':
        producer.send('positive-interactions', message)
    else:
        producer.send('negetive-interactions', message)
        
    producer.flush()
    return f"{interaction_type.capitalize()} action recorded for Item {item_id}, user_id: {user_id}"

async def handle_view_interaction(previous_intercation_message, user_id, item_id, interaction_type, rating=None, quantity=None):
    curr_message = build_intercation_payload(user_id, item_id, interaction_type, rating, quantity)
    if previous_intercation_message is not None:
        last_interaction_sentiment = determine_last_inter_sentiment(interaction_type, previous_intercation_message['payload']   ['interaction_type'], previous_intercation_message['payload']['rating'])
        interaction_output = send_interaction(previous_intercation_message, last_interaction_sentiment)
    else:
        interaction_output = ''
    return interaction_output, curr_message

# Function to determine sentiment
def determine_last_inter_sentiment(interaction_type, last_interaction_type, last_inter_rating=None):
    print(interaction_type)
    print(last_interaction_type)
    if last_interaction_type == 'view' and (interaction_type == 'view' or interaction_type is None):
        return 'negative'  # Views are negative unless followed by positive actions
    if last_interaction_type == 'rate' and last_inter_rating in [1, 2]:
        return 'negative'
    return 'positive'

# Function to display item and handle navigation
def display_item(index, items_df):
    index = int(index)
    if index < 0:
        index = 0
    elif index >= len(items_df):
        index = len(items_df) - 1

    row = items_df.iloc[index]
    item_display = (f'''
        | Field | Value |
        |-------|-------|
        | **Item ID** | {row['item_id']} |
        | **Category** | {row['category']} |
        | **Subcategory** | {row['subcategory']} |
        | **Price** | ${row['price']:.2f} |
        | **Average Rating** | {row['avg_rating']:.1f} |
        | **Number of Ratings** | {row['num_ratings']} |
        | **Popular** | {'Yes' if row['popular'] else 'No'} |
        | **New Arrival** | {'Yes' if row['new_arrival'] else 'No'} |
        | **On Sale** | {'Yes' if row['on_sale'] else 'No'} |'''
    )
    return (
        index,
        item_display,
        row['item_id'],
        f"Item {index + 1} of {len(items_df)}"
    )

# Custom CSS
css = """
.gradio-container {
    max-width: 800px !important;
    margin: auto;
    padding: 10px;
    overflow-x: auto;
}
.gr-button, .gr-input, .gr-textbox, .gr-markdown, .gr-dropdown {
    font-size: 14px !important;
}
"""

with gr.Blocks(css=css) as demo:
    items_df_state = gr.State(pd.DataFrame())
    last_message = gr.State(value=None)  # Track pending view interaction
    gr.Markdown("# Retail Store Demo")
    with gr.Row():
        with gr.Column():
            item_markdown = gr.Markdown("## Item 1")
            index = gr.State(value=0)
            item_id_state = gr.State()
            item_display = gr.Markdown()
        with gr.Column():
            with gr.Row():
                user_id = gr.Number(label="Enter your user ID", value=1, minimum=1, maximum=1000)
                nav_status = gr.Textbox(label="Navigation", interactive=False)
            with gr.Row():
                prev_btn = gr.Button("Previous item")
                next_btn = gr.Button("Next item")
            with gr.Row():
                with gr.Column():
                    with gr.Row():
                        quantity = gr.Number(label="Quantity", value=1, minimum=1, maximum=3)
                        with gr.Column():
                            cart_btn = gr.Button("Add to Cart")
                            purchase_btn = gr.Button("Purchase")
                with gr.Column():
                    with gr.Row():
                        rating = gr.Dropdown(choices=list(range(1,6)), label="Rating", min_width=1)
                        rate_btn = gr.Button("Rate", min_width=3)
            interaction_output = gr.Textbox(label="Interaction Status")


    # Initial display
    demo.load(
        fn=load_items_exiting_user,
        inputs=user_id,
        outputs=[items_df_state, index]
    ).then(
        fn=display_item,
        inputs=[index, items_df_state],
        outputs=[index, item_display, item_id_state, nav_status]
    ).then(
        fn=handle_view_interaction,
        inputs=[last_message, user_id, item_id_state, gr.State(value='view')],
        outputs=[interaction_output, last_message]
    )

    # Navigation button handlers
    prev_btn.click(
        fn=lambda idx: idx - 1,
        inputs=index,
        outputs=index
    ).then(
        fn=display_item,
        inputs=[index, items_df_state],
        outputs=[index, item_display, item_id_state, nav_status]
    ).then(
        fn=handle_view_interaction,
        inputs=[last_message, user_id, item_id_state, gr.State(value='view')],
        outputs=[interaction_output, last_message]
    ).then(
        fn=lambda id: f'## Item {id}',
        inputs=item_id_state,
        outputs=item_markdown
    )

    next_btn.click(
        fn=lambda idx: idx + 1,
        inputs=index,
        outputs=index
    ).then(
        fn=display_item,
        inputs=[index, items_df_state],
        outputs=[index, item_display, item_id_state, nav_status]
    ).then(
        fn=handle_view_interaction,
        inputs=[last_message, user_id, item_id_state, gr.State(value='view')],
        outputs=[interaction_output, last_message]
    ).then(
        fn=lambda id: f'## Item {id}',
        inputs=item_id_state,
        outputs=item_markdown
    )

    cart_btn.click(
        fn=handle_view_interaction,
        inputs=[last_message, user_id, item_id_state, gr.State(value='cart')],
        outputs=[interaction_output, last_message]
    )
    purchase_btn.click(
        fn=handle_view_interaction,
        inputs=[last_message, user_id, item_id_state, gr.State(value='purchase'), gr.State(value=None), quantity],
        outputs=[interaction_output, last_message]
    )
    rate_btn.click(
        fn=handle_view_interaction,
        inputs=[last_message, user_id, item_id_state, gr.State(value='rate'), rating, gr.State(value=None)],
        outputs=[interaction_output, last_message]
    )

    user_id.input(
        fn=handle_view_interaction,
        inputs=[last_message, user_id, item_id_state, gr.State(value='view')],
        outputs=[interaction_output, last_message]
    ).then(
        fn=load_items_exiting_user,
        inputs=user_id,
        outputs=[items_df_state, index]
    ).then(
        fn=display_item,
        inputs=[index, items_df_state],
        outputs=[index, item_display, item_id_state, nav_status]
    )

    # Handle app close 
    # this is bug the closure is created 
    demo.unload(lambda :handle_view_interaction(last_message, user_id, item_id_state, gr.State(value='None')))

# Launch the Gradio app
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=8080)