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