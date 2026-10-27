# AWS Deployment Guide for YouTube AI Assistant

This guide walks you through deploying the **YouTube AI Assistant** FastAPI backend to AWS so your Chrome extension can communicate with it from anywhere.

---

## 🎯 Best AWS Option for Your Setup: AWS App Runner

Since you have **AWS Free Tier and $100 in AWS credits**, **AWS App Runner** is the recommended choice:

| Feature | AWS App Runner | AWS EC2 (VM) |
|---|---|---|
| **Free HTTPS / SSL URL** | ✅ **Built-in free SSL** (`https://xxx.awsapprunner.com`) | ❌ Requires custom domain + Certbot/Nginx |
| **Server Management** | ✅ Fully managed (zero Linux maintenance) | ❌ Manual updates, firewall, systemd |
| **Streaming Support** | ✅ Native streaming (`/ask/stream`, `/speak`) | ✅ Needs proper Nginx proxy buffering config |
| **Cost** | ~$5–$10/month (easily covered by $100 credits) | Free tier for t3.micro* or ~$15/mo for t3.small |
| **Setup Time** | ~10 minutes | ~30 minutes |

> [!NOTE]
> Why HTTPS is required: Chrome Manifest V3 extensions block HTTP connections to remote IPs/domains for security. App Runner gives you a valid HTTPS URL out of the box without purchasing a domain.

---

## Option 1: Deploy with AWS App Runner (Recommended)

You can deploy directly using your GitHub repository (`piushlibra-arch/youtube-voice-bot`).

### Step 1: Push your code to GitHub
Make sure your latest code (including `backend/Dockerfile` and `backend/.dockerignore`) is pushed to your GitHub repository:
```bash
git add backend/Dockerfile backend/.dockerignore backend/app/services/transcript.py backend/.env.example docker-compose.yml extension/
git commit -m "Add Dockerfile and AWS deployment configs"
git push origin main
```

### Step 2: Open AWS App Runner Console
1. Log in to the [AWS Management Console](https://console.aws.amazon.com/).
2. In the top search bar, search for **App Runner** and click it.
3. Make sure your AWS region (top-right corner) is set to **US East (N. Virginia) `us-east-1`** or your nearest region (e.g. `ap-south-1` for Mumbai).
4. Click **Create an App Runner service**.

### Step 3: Source & Deployment Settings
1. **Repository type**: Select **Source code repository**.
2. Click **Add new** under GitHub connection, authorize AWS to access your GitHub account, and select your repository:
   - **Repository**: `piushlibra-arch/youtube-voice-bot`
   - **Branch**: `main`
3. **Deployment trigger**: Select **Automatic** (so every time you push code to GitHub, AWS automatically rebuilds and deploys).
4. Click **Next**.

### Step 4: Configure Build Settings
1. **Configuration file**: Select **Configure all settings here**.
2. **Runtime**: Select **Python 3**.
3. **Build command**:
   ```bash
   pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && pip install -r backend/requirements.txt
   ```
4. **Start command**:
   ```bash
   cd backend && uvicorn main:app --host 0.0.0.0 --port 8000
   ```
5. **Port**: Enter `8000`.
6. Click **Next**.

> [!TIP]
> **Alternative (Container Build)**: If you prefer Docker container build instead of source runtime, select **Container registry** > **Amazon ECR** or use App Runner's Dockerfile mode by pointing the Dockerfile path to `backend/Dockerfile`.

### Step 5: Service Configuration & Environment Variables
1. **Service name**: Enter `youtube-voice-bot`.
2. **Virtual CPU & Memory**:
   - **vCPU**: `1 vCPU`
   - **Memory**: `2 GB` *(PyTorch + embedding model requires ~1GB–1.5GB RAM)*.
3. **Environment variables**: Add the following:
   | Key | Value | Description |
   |---|---|---|
   | `GEMINI_API_KEY` | `your-gemini-key` | Google Gemini API key |
   | `CARTESIA_API_KEY` | `your-cartesia-key` | Cartesia TTS API key (optional if only using text) |
   | `GEMINI_MODEL` | `gemini-2.5-flash` | Main Gemini model |
   | `GEMINI_THINKING_LEVEL` | `low` | Fast response mode |
   | `YOUTUBE_PROXY` | *(optional)* | HTTP/HTTPS proxy if YouTube blocks AWS IPs |

4. Scroll down to **Health check**:
   - **Protocol**: `HTTP`
   - **Path**: `/health`
   - **Interval**: `10` seconds
   - **Timeout**: `5` seconds
   - **Healthy threshold**: `1`
   - **Unhealthy threshold**: `3`
5. Click **Next**, review the configuration, and click **Create & deploy**.

### Step 6: Get Your Service URL
1. Deployment takes about 3–5 minutes.
2. Once the status turns to **Running**, copy the **Default domain** URL (e.g. `https://ab12cd34ef.us-east-1.awsapprunner.com`).
3. Test it in your browser: `https://ab12cd34ef.us-east-1.awsapprunner.com/health`.
   You should see:
   ```json
   {"status":"ok","embedding_model_loaded":true,...}
   ```

---

## Option 2: Deploy to AWS EC2 (Virtual Machine)

If you prefer having full SSH access to a dedicated Linux machine:

### 1. Launch Instance
1. In AWS Console, go to **EC2** > **Launch Instance**.
2. **Name**: `youtube-voice-bot-server`.
3. **OS**: **Ubuntu 24.04 LTS**.
4. **Instance type**: `t3.small` (2 vCPU, 2 GB RAM).
   *(Note: `t3.micro` only has 1 GB RAM and can run out of memory when loading sentence-transformers unless you configure a 2 GB swapfile).*
5. **Key pair**: Create or select an existing key pair (`.pem`).
6. **Network Settings**:
   - Check **Allow SSH traffic from Anywhere** (or My IP).
   - Check **Allow HTTP traffic from the internet**.
   - Check **Allow HTTPS traffic from the internet**.
7. Click **Launch Instance**.

### 2. Connect and Install Docker
SSH into your instance:
```bash
ssh -i your-key.pem ubuntu@<your-ec2-public-ip>
```
Run this script to install Docker and clone the project:
```bash
# Update and install Docker
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker ubuntu
newgrp docker

# Clone repository
git clone https://github.com/piushlibra-arch/youtube-voice-bot.git
cd youtube-voice-bot

# Configure environment
cp backend/.env.example backend/.env
nano backend/.env    # paste your GEMINI_API_KEY and CARTESIA_API_KEY
```

### 3. Run with Docker Compose
```bash
docker compose up -d --build
```
Check container logs:
```bash
docker compose logs -f
```

---

## 🔌 Connecting the Chrome Extension to AWS

Once your backend is live on AWS:

1. Open `extension/popup.js`.
2. Update line 2 with your AWS App Runner URL (or EC2 HTTPS URL):
   ```javascript
   let API = "https://ab12cd34ef.us-east-1.awsapprunner.com";
   ```
3. In Chrome, go to `chrome://extensions`.
4. Click the **Reload** (circular arrow) icon on the **YouTube AI Assistant** card.
5. Open any YouTube video and click the extension icon. It will now connect to your AWS backend!

---

## ⚠️ Important Note: YouTube IP Blocking & Proxy

Cloud providers (AWS, GCP, DigitalOcean) are sometimes blocked by YouTube for transcript fetching (`youtube-transcript-api`), returning a 429 or `IpBlocked` error.

If you encounter this:
1. Get a proxy (for example, [Webshare.io](https://www.webshare.io/) provides 10 free proxies).
2. Set the `YOUTUBE_PROXY` environment variable in your AWS App Runner settings:
   ```
   YOUTUBE_PROXY=http://username:password@proxy-host:port
   ```
3. The backend will automatically route transcript fetches through this proxy.

---

## 💰 Managing Your $100 Credits & Costs

- **App Runner**: Pausing the service when you're not using it reduces cost to ~$0.007/GB-hr. You can pause it directly from the AWS App Runner console with one click (**Actions** > **Pause service**) and resume when needed.
- **Budget Alert**: Set up an AWS Zero-Spend / Budget Alert at [AWS Billing & Cost Management](https://console.aws.amazon.com/billing/) to notify you when 50% or 80% of your $100 credit is consumed.
