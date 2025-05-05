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
kafka_service = 'xray-cluster-kafka-bootstrap.jary-feast-example.svc.cluster.local:9092'
producer = KafkaProducer(
    bootstrap_servers=kafka_service,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)
items_df = pd.read_parquet('recommendation_items.parquet')

# Function to send interaction to Kafka
async def send_interaction(user_id, item_id, interaction_type, rating=None, quantity=None):
    interaction = {
        'user_id': int(user_id),  # Convert to Python int
        'item_id': int(item_id),  # Convert to Python int
        'timestamp': datetime.now().isoformat(),
        'interaction_type': interaction_type,
        'rating': int(rating) if rating is not None else None, 
        'quantity': int(quantity) if quantity is not None else None 
    }
    # print(interaction)
    producer.send('interactions', interaction)
    producer.flush()
    return f"{interaction_type.capitalize()} action recorded for Item {item_id}, user_id: {user_id}"


# Function to display item and handle navigation
def display_item(index, items_df):
    index = int(index)  # Ensure index is an integer
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
        row['item_id'],  # Pass item_id for interactions
        f"Item {index + 1} of {len(items_df)}"  # Navigation status
    )

# def load_items(item_ids: List[int]):
#     return items_df[items_df['item_id'].isin(item_ids)]

# Custom CSS to limit content width to 400px
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
# with gr.Blocks() as demo:
    # items_ids_state = gr.State([])
    items_df_state = gr.State(pd.DataFrame())
    gr.Markdown("# Retail Store Demo")
    with gr.Row():
        
        with gr.Column():
            item_markdown = gr.Markdown("## Item 1")
            index = gr.State(value=0)  # Track current item index
            item_id_state = gr.State()  # Store current item_id for interactions
            item_display = gr.Markdown()  # Display item details
        
        with gr.Column():
            with gr.Row():
                user_id = gr.Number(label="Enter your user ID", value=1, minimum=1, maximum=1000)
                nav_status = gr.Textbox(label="Navigation", interactive=False)  # Show current item position
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
        fn=send_interaction,
        inputs=[user_id, item_id_state, gr.State(value='view')],
        outputs=interaction_output
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
        fn=send_interaction,
        inputs=[user_id, item_id_state, gr.State(value='view')],
        outputs=interaction_output
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
        fn=send_interaction,
        inputs=[user_id, item_id_state, gr.State(value='view')],
        outputs=interaction_output
    ).then(
        fn=lambda id: f'## Item {id}',
        inputs=item_id_state,
        outputs=item_markdown
    )


    # Interaction handlers
    cart_btn.click(
        fn=send_interaction,
        inputs=[user_id, item_id_state, gr.State(value='cart')],
        outputs=interaction_output
    )
    purchase_btn.click(
        fn=send_interaction,
        inputs=[user_id, item_id_state, gr.State(value='purchase'), gr.State(value=None), quantity],
        outputs=interaction_output
    )
    rate_btn.click(
        fn=send_interaction,
        inputs=[user_id, item_id_state, gr.State(value='rate'), rating, gr.State(value=None)],
        outputs=interaction_output
    )
    
    user_id.input(
        fn=send_interaction,
        inputs=[user_id, item_id_state, gr.State(value='view')],
        outputs=interaction_output
    ).then(
        fn=load_items_exiting_user,
        inputs=user_id,
        outputs=[items_df_state, index]
    ).then(
        fn=display_item,
        inputs=[index, items_df_state],
        outputs=[index, item_display, item_id_state, nav_status]
    )


# Launch the Gradio app
if __name__ == "__main__":
    demo.launch()