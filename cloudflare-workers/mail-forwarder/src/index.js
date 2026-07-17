// Cloudflare Worker — ZICORE Mail Forwarder
// Receives email via Cloudflare Email Routing and forwards to ZICORE server API
//
// Deploy: wrangler deploy
// Config: wrangler.toml (zone = zicore.space)
//
// How it works:
// 1. Someone sends email to user@zicore.space
// 2. Cloudflare Email Routing receives it (MX records)
// 3. This Worker is triggered with the email data
// 4. Worker parses the email and POSTs to ZICORE API
// 5. ZICORE stores it in the local mailbox

export default {
  async email(message, env, ctx) {
    const to = message.to;
    const from = message.from;
    const subject = message.headers.get("subject") || "(sin asunto)";
    
    // Read the raw email body
    let rawEmail = "";
    try {
      rawEmail = await new Response(message.raw).text();
    } catch (e) {
      rawEmail = "(error reading email body)";
    }

    // Parse simple headers from raw email
    const headers = {};
    const headerSection = rawEmail.split("\r\n\r\n")[0] || "";
    for (const line of headerSection.split("\r\n")) {
      if (line.includes(":")) {
        const [key, ...vals] = line.split(":");
        headers[key.trim().toLowerCase()] = vals.join(":").trim();
      }
    }

    // Extract body (everything after first blank line)
    const bodyParts = rawEmail.split("\r\n\r\n");
    let body = bodyParts.length > 1 ? bodyParts.slice(1).join("\r\n\r\n") : "";

    // Decode quoted-printable if needed
    if (headers["content-transfer-encoding"] === "quoted-printable") {
      body = body.replace(/=\r?\n/g, "").replace(/=([0-9A-Fa-f]{2})/g, (_, hex) => 
        String.fromCharCode(parseInt(hex, 16))
      );
    }

    // Build payload for ZICORE API
    const payload = {
      to: to,
      from: from,
      subject: subject,
      body: body.slice(0, 50000), // Limit to 50KB
      headers: {
        "message-id": headers["message-id"] || "",
        "date": headers["date"] || new Date().toISOString(),
        "reply-to": headers["reply-to"] || from,
        "content-type": headers["content-type"] || "text/plain",
      },
      raw_size: rawEmail.length,
    };

    // Forward to ZICORE server
    const ZICORE_API = env.ZICORE_API_URL || "https://zcs.zicore.space";
    const API_SECRET = env.ZICORE_API_SECRET || "zicore-mail-worker-2026";
    
    try {
      const resp = await fetch(`${ZICORE_API}/api/mail/incoming`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Mail-Secret": API_SECRET,
        },
        body: JSON.stringify(payload),
      });

      const result = await resp.json();
      
      if (result.status === "ok") {
        console.log(`Email forwarded: ${from} -> ${to} (${subject})`);
      } else {
        console.error(`Failed to forward email: ${JSON.stringify(result)}`);
        // Don't reject - we still want to store it
      }
    } catch (e) {
      console.error(`Error forwarding to ZICORE: ${e.message}`);
    }

    // Also store a copy via Cloudflare Email Routing fallback
    // (in case ZICORE server is down)
    try {
      // Forward to Gmail as backup
      const GMAILForward = env.GMAIL_FORWARD || "jilocomption@gmail.com";
      // Cloudflare will handle the forwarding via Email Routing rules
    } catch (e) {}

    // Accept the email (don't reject)
    return;
  },
};
