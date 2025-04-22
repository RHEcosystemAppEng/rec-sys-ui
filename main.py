import gradio as gr
import pandas as pd
from kafka import KafkaProducer
import json
from datetime import datetime
from utils import load_items_exiting_user
from feast import FeatureStore
# Load items from Parquet file
store = FeatureStore('')
# Kafka producer setup
# producer = KafkaProducer(bootstrap_servers='localhost:9092', value_serializer=lambda v: json.dumps(v).encode('utf-8'))

# Function to send interaction to Kafka
def send_interaction(user_id, item_id, interaction_type, rating=None, quantity=None):
    interaction = {
        'user_id': user_id,
        'item_id': item_id,
        'timestamp': datetime.now().isoformat(),
        'interaction_type': interaction_type,
        'rating': rating,
        'quantity': quantity
    }
    # producer.send('interactions', interaction)
    # producer.flush()
    return f"{interaction_type.capitalize()} action recorded for Item {item_id}, user_id: {user_id}"


# Function to display item and handle navigation
def display_item(index, user_id, items_df):
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
        | **On Sale** | {'Yes' if row['on_sale'] else 'No'} |
        | **Arrival Date** | {row['arrival_date'].strftime('%Y-%m-%d')} |'''
    )

    return (
        index,
        item_display,
        row['item_id'],  # Pass item_id for interactions
        f"Item {index + 1} of {len(items_df)}"  # Navigation status
    )

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
    items_df = pd.read_parquet('recommendation_items.parquet')
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
                # item_id = gr.Number(label="Enter item ID", value=1, minimum=1, maximum=len(items_df))
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
        fn=display_item,
        inputs=[index, user_id, items_df],
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
        inputs=[index, user_id, items_df],
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
        inputs=[index, user_id, items_df],
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
        inputs=[store, user_id],
        outputs=items_df
    )

# Launch the Gradio app
if __name__ == "__main__":
    demo.launch()