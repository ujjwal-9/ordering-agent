// Load environment variables from .env file
require('dotenv').config({ path: '../.env' });

const express = require('express');
const Retell = require('retell-sdk').Retell;
const twilio = require('twilio');
const VoiceResponse = twilio.twiml.VoiceResponse;

// Create Express app
const app = express();
app.use(express.json());

console.log(process.env.RETELL_API_KEY);

// Initialize Retell client with API key from environment variable
const client = new Retell({
  apiKey: process.env.RETELL_API_KEY,
});

console.log(client);

// Voice webhook endpoint
app.post("/voice-webhook", async (req, res) => {
  try {
    // Register the phone call to get call id
    const phoneCallResponse = await client.call.registerPhoneCall({
      agent_id: process.env.RETELL_AGENT_ID,
      direction: "inbound", // optional
    });
    console.log(phoneCallResponse);

    // Start phone call websocket
    const voiceResponse = new VoiceResponse();
    const dial = voiceResponse.dial();
    dial.sip(
      `sip:${phoneCallResponse.call_id}@5t4n6j0wnrl.sip.livekit.cloud`,
    );
    res.set("Content-Type", "text/xml");
    res.send(voiceResponse.toString());
  } catch (error) {
    console.error('Error handling webhook:', error);
    res.status(500).send('Internal Server Error');
  }
});

// Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});