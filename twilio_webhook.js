// Load environment variables from .env file
require('dotenv').config({path: '.env'});

const express = require('express');
const Retell = require('retell-sdk').Retell;
const twilio = require('twilio');
const VoiceResponse = twilio.twiml.VoiceResponse;

// Create Express app
const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true })); // For parsing application/x-www-form-urlencoded

// Initialize Retell client with API key from environment variable
console.log(process.env.RETELL_AGENT_ID);
const client = new Retell({
  apiKey: process.env.RETELL_API_KEY,
});

// Voice webhook endpoint
app.post("/voice-webhook", async (req, res) => {
  try {
    // Extract phone numbers from request
    const fromNumber = req.body.From || req.body.Caller;
    const toNumber = req.body.To || req.body.Called;
    
    console.log("Phone numbers extracted:", { fromNumber, toNumber });
    
    // Register the phone call to get call id
    const phoneCallResponse = await client.call.registerPhoneCall({
      agent_id: process.env.RETELL_AGENT_ID,
      direction: "inbound",
      from_number: fromNumber,
      to_number: toNumber,
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
const PORT = process.env.TWILIO_WEBHOOK_PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});