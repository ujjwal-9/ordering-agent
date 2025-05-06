# Phone Ordering System

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


# Retell Custom LLM Twilio Webhook

This is a simple Express server that handles Twilio voice webhooks and integrates with Retell's custom LLM service.

## Setup

1. Install dependencies:
   ```
   npm install
   ```

2. Configure your environment variables:
   - Create a `.env` file in the parent directory with the following variables:
     ```
     RETELL_API_KEY=your_retell_api_key_here
     RETELL_AGENT_ID=your_retell_agent_id_here
     PORT=3000
     ```
   - Replace `your_retell_api_key_here` with your actual Retell API key
   - Replace `your_retell_agent_id_here` with your actual Retell agent ID

3. Configure your Twilio account:
   - Set up a Twilio account if you don't have one
   - Configure your Twilio phone number to use this webhook URL for voice calls

## Running the Server

Development mode (with auto-restart):
```
npm run dev
```

Production mode:
```
npm start
```

The server will run on port 3000 by default. You can change this by setting the `PORT` environment variable in the `.env` file.

## Webhook Configuration

1. Make your server publicly accessible (using ngrok or similar)
2. Configure your Twilio phone number to use the webhook URL: `https://your-domain.com/voice-webhook`
3. Set the HTTP method to POST

## Customization

- The `agent_id` is now loaded from the environment variable `RETELL_AGENT_ID`
- Adjust the SIP domain if required by your Retell configuration 