# ConfigMat - Configuration Management for Data & Backend Teams (Under Development)


ConfigMat is an open-source configuration management platform built specifically for **Data Engineers** and **Backend Teams**. It solves the problem of "hardcoded configs" and "messy env files" by providing a centralized dashboard where technical leads can define templates, and non-technical stakeholders (product managers, analysts) can safely update configuration values without touching code.

## 🚀 Why ConfigMat?

*   **For Data Teams**: Manage ETL pipelines, updated thresholds, and A/B test parameters dynamically. No more redeploying pipelines just to change a variable.
*   **For Backend Teams**: Centralize feature flags and service configurations.
*   **For The Whole Team**: Enable non-technical members to manage their own settings via a user-friendly UI, governed by strict schemas you define.
*   **Secure**: Zero-Knowledge architecture ensures we (and your infra provider) never see your secrets.

## 🏗️ Architecture

```mermaid
graph TD
    User[Developer / PM] -->|UI Dashboard| API[ConfigMat API]
    SDK[Your App / Data Pipeline] -->|Pull Config| API
    SDK -.->|Local Cache| Cache[Local Config Cache]
    API -->|Read/Write| DB[(PostgreSQL)]
    API -->|Cache| Redis[(Redis)]
    
    subgraph "Your Infrastucture"
      API
      DB
      Redis
    end
```

## 🛠️ How to Use

### 1. Set up the Server

You can self-host ConfigMat easily using Render (recommended for MVP) or Docker.

**Deploy to Render:**
1.  Fork this repository.
2.  Sign up for [Render.com](https://render.com).
3.  New -> Blueprint -> Select this repo's `app/render.yaml`.
4.  Done! Your instance is live.

*(A fully managed SaaS version of ConfigMat is coming soon if you prefer not to manage infrastructure!)*

### 2. Install the CLI

Use the CLI to inject secrets and configs into your local development environment.

```bash
# MacOS / Linux
curl -fsSL https://raw.githubusercontent.com/configmat/cli/main/install.sh | bash

# Login to your instance
configmat login --host https://your-configmat-instance.com

# Run your app with injected config
configmat run -- python app.py
```

### 3. Integrate the SDK

Use the SDKs to fetch configuration dynamically in your code.

**Python:**
```bash
pip install configmat
```

```python
from configmat import ConfigMat

# Initialize (API Key injected via CLI or Env Var)
client = ConfigMat()

# Get a value (uses local cache if API is down)
feature_enabled = client.get("feature_flags.new_dashboard", default=False)
```

**Node.js:**
```bash
npm install @configmat/sdk
```

```javascript
import { ConfigMat } from '@configmat/sdk';

const config = await ConfigMat.load();
const isEnabled = config.get('feature_flags.new_dashboard');
```

