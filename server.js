import express from "express";
import bodyParser from "body-parser";
import fetch from "node-fetch";

const app = express();
app.use(bodyParser.json());

const QIWI_SECRET = "aaa76bbe79a13acb11b6c598ade3481b"; // Qiwi API токен
const QIWI_PUBLIC = "aaa76bbe79a13acb11b6c598ade3481b"; // Сайтта қолдану үшін

// Төлем жасау (invoice)
app.post("/create-invoice", async (req, res) => {
  const { amount, comment } = req.body;

  const response = await fetch("https://api.qiwi.com/partner/bill/v1/bills", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${QIWI_SECRET}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      amount: { currency: "RUB", value: amount },
      comment: comment,
      expirationDateTime: new Date(Date.now() + 15*60*1000).toISOString() // 15 минут
    })
  });

  const data = await response.json();
  res.json({ payUrl: data.payUrl });
});

// Qiwi төлем webhook (төлем өткенін тексереді)
app.post("/qiwi-callback", (req, res) => {
  const { bill } = req.body;
  
  if (bill.status.value === "PAID") {
    console.log("✅ Донат түсті:", bill.amount.value, bill.comment);

    // Осы жерде Minecraft серверіне команда жібере аласың
    // Мысалы: RCON арқылы Pro/Elite/Ultimate беру
  }

  res.sendStatus(200);
});

app.listen(3000, () => console.log("Server running on http://localhost:3000"));
