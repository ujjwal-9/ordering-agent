# Retell Custom LLM Python Demo

This is a demo of using Retell with a custom LLM in Python. The demo shows how to integrate Retell with OpenAI's API to create a voice AI agent for a burger restaurant ordering system.

## Features

- Real-time voice conversation with an AI agent
- Streaming responses for a more natural conversation flow
- Function calling support for more complex interactions
- Burger restaurant ordering system with natural language understanding
  - Understand spoken orders with quantities (e.g., "three burgers")
  - Confirm orders with callers
  - Handle customization options (cooking preferences, cheese types, toppings)
  - Provide order summaries
  - Suggest add-ons for items in the order
  - Handle order corrections
  - Suggest combo meals and drinks
  - Take customer name for the order
  - Confirm pickup or delivery preference
  - Provide estimated preparation time

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   RETELL_API_KEY=your_retell_api_key
   ```
4. Run the server:
   ```bash
   uvicorn app.server:app --reload
   ```

## Burger Restaurant Ordering System

The ordering system is designed to process natural language spoken orders from customers for a burger restaurant called "Burger Bliss". It includes:

1. **Natural Language Understanding**: The system can understand spoken orders and extract relevant information such as items, quantities, and modifiers.

2. **Order Confirmation**: After processing an order, the system will confirm it with the customer to ensure accuracy.

3. **Customization Handling**: The system can handle various customization options:
   - Cooking preferences (rare, medium-rare, medium, medium-well, well-done)
   - Cheese types (American, Cheddar, Swiss, Pepper Jack, Blue Cheese)
   - Toppings (lettuce, tomato, onion, pickles, jalapeños, mushrooms, special sauce, mayo, ketchup, mustard)
   - Sizes (small, medium, large)

4. **Order Summary**: The system provides a summary of the order, including all items and their modifiers.

5. **Add-on Suggestions**: The system suggests add-ons for items in the order, such as "Would you like cheese with your burger?"

6. **Combo Suggestions**: The system suggests combo meals when appropriate, such as "Would you like to make that a combo with fries and a drink for just $3 more?"

7. **Drink Suggestions**: The system suggests drinks if not already ordered.

8. **Order Corrections**: The system can handle corrections to the order, such as "No, it's two cheeseburgers and three fries."

9. **Customer Information**: The system takes the customer's name for the order and confirms pickup or delivery preference.

10. **Preparation Time**: The system provides an estimated preparation time for the order.

### How It Works

The ordering system consists of two main components:

1. **OrderHandler**: This class is responsible for processing orders and extracting information from the conversation transcript.

2. **OrderLlmClient**: This class extends the base LLM client to integrate with the order handling system.

The system uses a combination of rule-based processing and LLM-based responses to handle orders effectively.

### Menu Items

- **Burgers**: Classic Burger, Cheeseburger, Double Burger, Veggie Burger, Bacon Burger, Mushroom Swiss Burger, Bliss Signature Burger
- **Sides**: French Fries, Onion Rings, Side Salad, Cheese Fries, Loaded Fries
- **Beverages**: Coke, Diet Coke, Sprite, Dr. Pepper, Iced Tea, Lemonade, Water, Coffee, Milkshakes

### Pricing

- Basic Burger: $7.99
- Specialty Burgers: $9.99-$12.99
- Add-ons: $1-$2 each
- Sides: $2.99-$4.99
- Drinks: $1.99-$4.99
- Combos: Add $3 to any burger for medium fries and drink

### Example Conversation

```
Agent: Thanks for calling Burger Bliss! This is Julie, how can I help you today?
User: Hi, I'd like to order a cheeseburger.
Agent: Great choice! Would you like American, cheddar, or pepper jack cheese on your cheeseburger?
User: Cheddar please.
Agent: Perfect. How would you like your burger cooked? We recommend medium.
User: Medium is fine.
Agent: Got it. Would you like any toppings on your burger? We have lettuce, tomato, onions, pickles, and our special sauce.
User: Lettuce and tomato, but no onions please.
Agent: No problem. Would you like to make that a combo with fries and a drink for just $3 more?
User: Yes, that sounds good.
Agent: Excellent! What size fries would you like? We have small, medium, or large.
User: Medium is fine.
Agent: And what would you like to drink? We have Coke, Diet Coke, Sprite, Dr. Pepper, iced tea, or lemonade.
User: I'll have a medium Coke.
Agent: Let me confirm your order: You'd like one medium Cheeseburger with cheddar cheese, lettuce and tomato, no onions, a medium fries, and a medium Coke. Is that correct?
User: Yes, that's right.
Agent: Your total comes to $12.99. Can I get a name for your order?
User: Mike.
Agent: Thanks, Mike. Will you be picking up or would you like delivery?
User: I'll pick it up.
Agent: Great! We'll have your order ready for pickup in about 15 minutes. You can park in our designated pickup spots and we'll bring it right out. Is there anything else you need today?
User: No, that's all.
Agent: Thank you for your order, Mike! We appreciate your business and look forward to serving you. Have a great day!
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
