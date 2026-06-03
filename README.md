```markdown
# MzigoSafe

**MzigoSafe** is an offline-first, USSD-based logistics escrow platform designed to eliminate the trust deficit in the informal e-commerce sector. By leveraging a centralized ledger and a strict **Dual-OTP Chain of Custody**, MzigoSafe mathematically guarantees proof-of-delivery and instant M-Pesa payouts, protecting sellers, buyers, and delivery riders alike.

---

## 🚀 The Problem

The informal logistics market is crippled by a lack of trust:

* **Sellers** refuse to dispatch goods without upfront payment.
* **Buyers** refuse to pay before physically inspecting the item.
* **Both parties** fear the delivery rider might disappear with the package or the cash.

Current logistics applications require smartphones, active internet connections, and complex onboarding, alienating a massive portion of the market that relies on feature phones and USSD infrastructure.

## 💡 The Solution & Core Features

MzigoSafe operates entirely over USSD (`*384*...#`) and SMS, making it accessible to 100% of mobile users with zero data requirements.

* **Live M-Pesa Escrow:** Funds are securely locked in the system via Safaricom STK Push before a rider is ever dispatched.
* **Dual-OTP Verification:** The system generates two unique SMS OTPs. The rider cannot progress the delivery or get paid without physically collecting the **Pickup OTP** from the seller and the **Delivery OTP** from the buyer.
* **Universal Order Tracking:** Buyers and sellers can instantly check the real-time status of their package directly from the main menu using their phone number—no tracking IDs required.
* **Stateful USSD Engine:** Powered by a PostgreSQL session manager, the menus are fully crash-proof, remembering user states even if a session drops.
* **Reverse Logistics & Dispute Resolution:** Built-in flows allow riders to log buyer rejections at the door, automatically triggering item refunds to the buyer while securing the transit fee for the rider.

---

## 💸 Financial Architecture (Daraja API)

MzigoSafe utilizes an asynchronous event-driven architecture to handle Safaricom's Daraja API, ensuring no funds are lost during network timeouts.

```mermaid
sequenceDiagram
    participant B as Buyer
    participant S as Seller
    participant R as Rider
    participant M as MzigoSafe API
    participant D as Daraja (Safaricom)

    Note over B,M: 1. Escrow Lock (C2B)
    B->>M: Approves Escrow via USSD
    M->>D: Trigger STK Push Request
    D-->>B: PIN Prompt on Phone
    B->>D: Enters M-Pesa PIN
    D-->>M: Asynchronous Webhook (Success)
    M->>M: Secure Ledger & Generate OTPs

    Note over R,M: 2. Automated Payouts (B2C)
    R->>M: Inputs Delivery OTP at Drop-off
    M->>M: Verify OTP & Break Escrow
    M->>D: B2C API (Item Price)
    D-->>S: Instant M-Pesa Deposit
    M->>D: B2C API (Delivery Fee)
    D-->>R: Instant M-Pesa Deposit

```

---

## 🛠️ Technical Architecture

### Tech Stack

* **Backend API:** Python, FastAPI
* **Database & ORM:** PostgreSQL, SQLAlchemy
* **Frontend Dashboard:** Jinja2 Templates, Tailwind CSS
* **Telecommunications:** Africa's Talking API (USSD & SMS)
* **Payments:** Safaricom Daraja API (M-Pesa Express & B2C)

### Core System Flow

| Phase | Actor | Action | Database State |
| --- | --- | --- | --- |
| **1. Initiation** | Seller | Dials USSD, inputs Buyer number, item price, and delivery fee. | `pending_buyer_payment` |
| **2. Escrow Trap** | Buyer | Dials USSD, STK Push triggers on phone. Webhook confirms payment. | `funds_secured` (OTPs sent) |
| **3. Dispatch & Pickup** | Rider | Accepts job via USSD, travels to Seller, inputs **Pickup OTP**. | `in_transit` |
| **4. Handover & Payout** | Rider | Hands package to Buyer, inputs **Delivery OTP**. | `delivered` (B2C Payouts fired) |
| **5. Dispute (Edge Case)** | Rider | Reports buyer rejection at drop-off. | `cancelled` (Refund issued) |

---

## ⚙️ Local Development Setup

### Prerequisites

* Python 3.8+
* PostgreSQL
* Africa's Talking Sandbox Account
* Safaricom Daraja Developer Account

### Installation

1. **Clone the repository:**
```bash
git clone [https://github.com/yourusername/mzigosafe.git](https://github.com/yourusername/mzigosafe.git)
cd mzigosafe

```


2. **Create a virtual environment and install dependencies:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

```


3. **Environment Variables:**
Create a `.env` file in the root directory and populate your API credentials:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/mzigosafe_db

# Africa's Talking
AT_USERNAME=sandbox
AT_API_KEY=your_sandbox_api_key

# Safaricom Daraja (M-Pesa)
MPESA_CONSUMER_KEY=your_key
MPESA_CONSUMER_SECRET=your_secret
MPESA_PASSKEY=your_passkey
MPESA_SHORTCODE=174379
MPESA_B2C_SHORTCODE=600986
MPESA_B2C_INITIATOR_NAME=testapi
MPESA_B2C_SECURITY_CREDENTIAL=your_encrypted_credential
MPESA_CALLBACK_URL=[https://your-ngrok-url.app/api/mpesa/callback](https://your-ngrok-url.app/api/mpesa/callback)

```


4. **Initialize the Database:**
Run the application once to allow SQLAlchemy to create the database schemas.
5. **Run the Application:**
```bash
uvicorn main:app --reload

```


6. **Expose Localhost:**
Use Ngrok to tunnel your local server and configure your webhooks.
```bash
ngrok http 8000

```


* *USSD Callback:* `https://<ngrok-url>/api/ussd`
* *M-Pesa Callback:* `https://<ngrok-url>/api/mpesa/callback`



---

## 🔮 Future Roadmap

* **Data Warehousing & BI:** Implement an extended star schema to extract transactional data into a dedicated warehouse, enabling comprehensive sales, route, and volume analysis via Power BI.
* **AI-Powered Predictive Logistics:** Utilize timestamp data from the stateful Dual-OTP system to train regression models (e.g., LightGBM) that forecast accurate delivery ETAs and optimize dynamic pricing based on historical route completion times.
* **Automated Agent Support:** Integrate a Retrieval-Augmented Generation (RAG) system utilizing advanced LLMs to handle tier-1 customer disputes, query routing, and automated USSD/WhatsApp support.
* **E-commerce API:** Provide an open REST API allowing external platforms, WhatsApp bots, and Instagram sellers to generate MzigoSafe escrow links automatically upon order confirmation.

```

***

<FollowUp label="What's the next mission?" query="With the code locked and documented, how do you want to proceed? Are you pushing this straight to your GitHub portfolio, or do you want to start architecting the predictive ETAs and data warehouse from the roadmap?"/>

```