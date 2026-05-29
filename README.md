# MzigoSafe

**MzigoSafe** is an offline, USSD-based logistics escrow platform designed to eliminate the trust deficit in the informal e-commerce sector. By leveraging a virtual ledger and a strict **Dual-OTP Chain of Custody**, MzigoSafe mathematically guarantees proof-of-delivery and instant payouts, protecting sellers, buyers, and delivery riders alike.

---

## 🚀 The Problem

The informal logistics market is crippled by a lack of trust:

* **Sellers** refuse to dispatch goods without upfront payment.
* **Buyers** refuse to pay before physically inspecting the item.
* **Both parties** fear the delivery rider might disappear with the package or the cash.
Current logistics applications require smartphones, active internet connections, and complex onboarding, alienating a massive portion of the market that relies on feature phones.

## 💡 The Solution

MzigoSafe operates entirely over USSD and SMS, making it accessible to 100% of mobile users.

1. **Virtual Escrow:** Funds are securely locked in the system before a rider is ever dispatched.
2. **Dual-OTP Verification:** The core innovation. The system generates two unique SMS OTPs. The rider cannot progress the delivery or get paid without physically collecting the **Pickup OTP** from the seller and the **Delivery OTP** from the buyer.

---

## 🛠️ Technical Architecture

### Tech Stack

* **Backend:** Python, FastAPI
* **Database:** PostgreSQL, SQLAlchemy (ORM)
* **Integrations:** Africa's Talking API (USSD Gateway & SMS Messaging)

### Core System Flow

| Phase | Actor | Action | Database State |
| --- | --- | --- | --- |
| **1. Initiation** | Seller | Dials USSD, inputs Buyer number, item price, and delivery fee. | `pending_buyer_payment` |
| **2. Escrow Trap** | Buyer | Dials USSD, is intercepted by the Escrow Prompt, and approves payment. | `funds_secured` (OTPs generated & SMS sent) |
| **3. Dispatch & Pickup** | Rider | Accepts job via USSD, travels to Seller, and inputs the **Pickup OTP**. | `in_transit` |
| **4. Handover & Payout** | Rider | Hands package to Buyer, inputs the **Delivery OTP**. | `delivered` (Funds instantly split to Seller & Rider) |

---

## ⚙️ Local Development Setup

### Prerequisites

* Python 3.8+
* PostgreSQL
* Africa's Talking Sandbox Account

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/mzigosafe.git
cd mzigosafe

```



```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt

```

3. **Environment Variables:**
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/mzigosafe_db
AT_USERNAME=sandbox
AT_API_KEY=your_sandbox_api_key

```



```

4. **Initialize the Database:**
   Execute the provided SQL schema in your PostgreSQL instance to create the `users`, `deliveries`, and `escrow_ledger` tables, along with the custom Enums.

5. **Run the Application:**
   ```bash
uvicorn main:app --reload

```

6. **Expose to Africa's Talking:**
Use Ngrok to tunnel your local server and paste the HTTPS URL into your Africa's Talking Sandbox USSD callback settings.
```bash
ngrok http 8000

```



```

---

## 🔮 Future Roadmap
*   **Live API Integration:** Transition the virtual ledger to live M-Pesa STK Pushes via the Safaricom Daraja API.
*   **Predictive Analytics & ML:** Utilize the timestamp data from the Dual-OTP system to train machine learning models that predict accurate delivery ETAs and optimize rider-to-job matching based on historical route completion times.
*   **E-commerce API:** Provide an open API allowing platforms like Instagram or WhatsApp bots to generate MzigoSafe escrow links automatically upon order confirmation.

```