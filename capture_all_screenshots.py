"""
Enhanced Screenshot Capture Script
"""
import os
import sys
import time
import subprocess
import requests
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath("outputs_screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print(f"Server is responding at {url}!")
                return True
        except Exception:
            pass
        time.sleep(1)
    return False

def main():
    port = 8505
    url = f"http://localhost:{port}"
    print(f"Starting Streamlit via {sys.executable} on port {port}...", flush=True)
    
    server_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "agentic_dashboard.py", "--server.port", str(port), "--server.headless", "true"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    try:
        if not wait_for_server(url, timeout=30):
            print(f"Failed to connect to Streamlit at {url} within 30 seconds.")
            return

        print(f"Connecting Playwright to {url}...", flush=True)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # High-resolution 1920x1080 viewport with crisp scale
            context = browser.new_context(viewport={"width": 1680, "height": 1050}, device_scale_factor=1.25)
            page = context.new_page()
            
            print("Navigating to Dashboard...", flush=True)
            page.goto(url, wait_until="networkidle", timeout=45000)
            
            # Wait for Streamlit app to complete initial run
            print("Waiting for tabs to appear...", flush=True)
            page.wait_for_selector('button[data-testid="stTab"], [role="tab"]', timeout=30000)
            time.sleep(6)  # Allow map & tiles to fully render
            
            # 1. Overview & Map Tab
            p1 = os.path.join(OUTPUT_DIR, "01_Agentic_Dashboard_Overview.png")
            print(f"Saving {p1}...", flush=True)
            page.screenshot(path=p1, full_page=False)
            
            # Find tabs
            tabs = page.query_selector_all('button[data-testid="stTab"], [role="tab"]')
            print(f"Found {len(tabs)} tabs.", flush=True)
            for idx, tab in enumerate(tabs):
                print(f"Tab {idx}: {tab.inner_text()}")
            
            # 2. Multi-Agent Reasoning Feed
            if len(tabs) >= 2:
                print("Clicking Tab 2...", flush=True)
                tabs[1].click()
                time.sleep(4)
                p2 = os.path.join(OUTPUT_DIR, "02_Multi_Agent_Reasoning_Feed.png")
                page.screenshot(path=p2, full_page=False)
                
            # 3. Incident Commander Copilot
            if len(tabs) >= 3:
                print("Clicking Tab 3: Copilot...", flush=True)
                tabs[2].click()
                time.sleep(3)
                p3 = os.path.join(OUTPUT_DIR, "03_Incident_Commander_Copilot_Chat.png")
                page.screenshot(path=p3, full_page=False)
                
            # 4. Autonomous Dispatch Matrix
            if len(tabs) >= 4:
                print("Clicking Tab 4: Dispatch Matrix...", flush=True)
                tabs[3].click()
                time.sleep(3)
                p4 = os.path.join(OUTPUT_DIR, "04_Autonomous_Fleet_Dispatch_Matrix.png")
                page.screenshot(path=p4, full_page=False)
                
            # 5. ML Ensemble Performance
            if len(tabs) >= 5:
                print("Clicking Tab 5: ML Performance...", flush=True)
                tabs[4].click()
                time.sleep(4)
                p5 = os.path.join(OUTPUT_DIR, "05_ML_Ensemble_Model_Comparison.png")
                page.screenshot(path=p5, full_page=False)
                
            browser.close()
            print("\nSUCCESS: All 5 high-resolution screenshots generated in outputs_screenshots/!", flush=True)
            
    except Exception as e:
        print(f"Exception during capture: {e}", flush=True)
    finally:
        server_process.terminate()
        try:
            server_process.kill()
        except:
            pass
        print("Server terminated cleanly.", flush=True)

if __name__ == "__main__":
    main()
