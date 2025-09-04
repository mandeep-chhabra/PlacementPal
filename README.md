````
# 🎓✨ PlacementPal - Your Smart Placement Reminder Assistant ✨🎓

**🚀 Never miss an opportunity – PlacementPal fetches placement-related emails, lets you approve them, and creates reminders on Google Calendar with Telegram notifications.**
<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="900">

---

## 🌟 Why PlacementPal?
**Job and placement opportunities often get buried in a crowded inbox. PlacementPal ensures you never miss an important drive, interview, or test deadline. By integrating Gmail, Google Calendar, and Telegram, PlacementPal acts as your personal placement coordinator.**

✅ No more missed deadlines
✅ Simple approve-and-schedule system
✅ Instant Telegram reminders

<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="900">

---

## 🚀 Key Features

### 📩 1. Smart Email Extraction
- Fetches all placement-related emails from Gmail.
- Filters only relevant opportunities.

### ✅ 2. Approval Workflow
- Sends Telegram message with **Approve / Ignore** buttons.
- Adds to Google Calendar only when **Approved**.

### ⏰ 3. Automated Reminders
- Calendar events created with correct scheduled time.
- Telegram reminders before deadlines.

### 🔔 4. Multi-Platform Support
- Python Bot implementation.
- Low-code workflow with **n8n**.

---

## 🛠️ Tech Stack

### Core Tools
- **Python** 🐍 (Gmail API + Google Calendar API + Telegram Bot API)
- **n8n** ⚙️ (No-code workflow automation)

### APIs Used
- Gmail API
- Google Calendar API
- Telegram Bot API

### Other Tools 🔧
- Google Cloud Console
- ngrok (optional for webhook testing)
- Git & GitHub

<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="900">

---

## 🛠️ Installation Guide

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/PlacementPal.git](https://github.com/your-username/PlacementPal.git)
cd PlacementPal
````

### 🔹 Option A: Python Implementation

### 2\. Setup Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### 3\. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4\. Setup Google APIs

  - Go to **Google Cloud Console**
  - Enable **Gmail API & Google Calendar API**
  - Create **OAuth credentials → Download credentials.json**
  - Place it inside project root

### 5\. Run the Bot

```bash
python placementpal.py
```

-----

### 🔹 Option B: n8n Workflow

### 2\. Install n8n

```bash
npm install n8n -g
```

### 3\. Start n8n

```bash
n8n start
```

### 4\. Import Workflow

  - Open `http://localhost:5678`
  - Import the provided `PlacementPal-n8n.json`
  - Add your Gmail & Telegram credentials in `n8n Settings → Credentials`

-----

### ⚙️ Environment Variables

Create a `.env` file for Python bot:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

For n8n, set credentials via UI.

-----

### 📸 Demo Flow

  - **Gmail** → Fetch placement email
  - **Telegram** → Bot sends message with **Approve** button
  - On approval → Event gets added to **Google Calendar**
  - **Telegram** sends reminder before deadline

\<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="900"\>

-----

### ⚠️ Troubleshooting

  - **Gmail not fetching emails**
      - Ensure Gmail API enabled & valid OAuth credentials.
      - Delete `token.json` and re-run for fresh authorization.
  - **Telegram not sending messages**
      - Verify Bot Token & Chat ID.
      - Use `/start` in Telegram to activate the bot.
  - **n8n Workflow Error**
      - Double-check credentials are assigned.
      - Ensure workflow is activated after testing.

-----

### 📊 Project Status

✅ Gmail + Calendar Bot ready
✅ Telegram Approvals working
✅ n8n Workflow tested
🚧 Future: Slack / WhatsApp integration

-----

### 🏷️ Badges

(Image of badges would be here)

-----

### 👨‍💻 Author

Mandeep Singh Chhabra
📍 Indore, India
🔗 LinkedIn | GitHub

-----

### 📜 License

This project is licensed under the MIT License – see the LICENSE file for details.

\<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="900"\>

```
```
