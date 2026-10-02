import streamlit as st
from openai import OpenAI
import subprocess
import json
import os

# ----------------------------------------
# 1. ตั้งค่าหน้าเว็บ UI
# ----------------------------------------
st.set_page_config(page_title="Ultimate AI Workspace", page_icon="🚀", layout="wide")
st.title("🚀 My Ultimate AI Workspace")
st.markdown("แชท, สั่งงาน Terminal, แนบไฟล์ และสร้างโปรแกรม พร้อมระบบจัดการ API หลายโมเดล")

# ----------------------------------------
# 2. ตั้งค่า State เริ่มต้น (หน่วยความจำของเว็บ)
# ----------------------------------------
# ค่าเริ่มต้นสำหรับ API ตัวแรกที่คุณให้มา
if "api_configs" not in st.session_state:
    st.session_state.api_configs = {
        "pp/claude-opus-5.5": {
            "base_url": "https://n8n.carwraman.shop/v1",
            "api_key": "sk-807d1f1ecf22bfa0-80e207-4490935c"
        }
    }

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "คุณคือ AI Agent ระดับสูง คุณทำงานอยู่บนเครื่องของผู้ใช้ มีสิทธิ์รัน Terminal และสร้างไฟล์ คุณสามารถอ่านไฟล์ที่ผู้ใช้อัปโหลดได้โดยการรันคำสั่ง terminal เช่น cat หรือ python หากผู้ใช้ให้งานมา ให้วิเคราะห์ รันคำสั่ง และสรุปผล หรือสร้างไฟล์ให้"}
    ]

if "downloadable_files" not in st.session_state:
    st.session_state.downloadable_files = {}

# ----------------------------------------
# 3. แถบเครื่องมือด้านข้าง (Sidebar)
# ----------------------------------------
with st.sidebar:
    st.header("⚙️ จัดการ API & โมเดล")
    
    # ส่วนเพิ่มโมเดลใหม่ (กดซ่อน/ขยายได้)
    with st.expander("➕ เพิ่มโมเดล / ใส่ API ใหม่", expanded=False):
        new_model = st.text_input("ชื่อ Model ID (เช่น gpt-4o, llama-3)")
        new_base_url = st.text_input("Base URL", value="https://n8n.carwraman.shop/v1")
        new_api_key = st.text_input("API Key", type="password")
        
        if st.button("💾 บันทึกข้อมูล"):
            if new_model and new_base_url and new_api_key:
                # บันทึกลงในระบบ
                st.session_state.api_configs[new_model] = {
                    "base_url": new_base_url,
                    "api_key": new_api_key
                }
                st.success(f"เพิ่ม {new_model} เข้าไปในตัวเลือกแล้ว!")
                st.rerun() # สั่งรีเฟรชหน้าเว็บเพื่อให้โมเดลใหม่โผล่ใน Dropdown
            else:
                st.error("กรุณากรอกข้อมูลให้ครบทุกช่อง")
    
    st.markdown("---")
    
    # Dropdown ให้ผู้ใช้เลือกโมเดลที่จะใช้คุย
    model_list = list(st.session_state.api_configs.keys())
    selected_model = st.selectbox("🤖 เลือกโมเดลที่ต้องการแชท", model_list)
    
    st.markdown("---")
    
    # ระบบแนบไฟล์
    st.header("📎 แนบไฟล์ให้ AI")
    uploaded_files = st.file_uploader("อัปโหลดไฟล์ที่นี่", accept_multiple_files=True)
    if uploaded_files:
        for file in uploaded_files:
            with open(file.name, "wb") as f:
                f.write(file.getbuffer())
        st.success(f"อัปโหลด {len(uploaded_files)} ไฟล์สำเร็จ!")
    
    st.markdown("---")
    
    # ระบบดาวน์โหลดไฟล์
    st.header("📥 ไฟล์ที่ AI สร้างให้")
    if not st.session_state.downloadable_files:
        st.info("ยังไม่มีไฟล์ที่สร้าง")
    else:
        for fname, fcontent in st.session_state.downloadable_files.items():
            st.download_button(label=f"⬇️ ดาวน์โหลด {fname}", data=fcontent, file_name=fname)
            
    st.markdown("---")
    # ปุ่มล้างแชท (ใช้เวลาเปลี่ยนโมเดลแล้วอยากเริ่มคุยใหม่)
    if st.button("🗑️ ล้างประวัติแชท"):
        st.session_state.messages = [st.session_state.messages[0]]
        st.session_state.downloadable_files = {}
        st.rerun()

# ----------------------------------------
# 4. ดึงการตั้งค่า API ตามโมเดลที่เลือก
# ----------------------------------------
if selected_model:
    active_config = st.session_state.api_configs[selected_model]
    client = OpenAI(
        base_url=active_config["base_url"],
        api_key=active_config["api_key"]
    )
else:
    st.warning("กรุณาเพิ่มและเลือกโมเดลก่อนใช้งาน")
    st.stop()

# ----------------------------------------
# 5. ฟังก์ชัน Tools สำหรับ AI
# ----------------------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "run_terminal",
            "description": "รันคำสั่ง OS Command Line (Linux) เช่น ls, cat, python, pip install",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "คำสั่งที่ต้องการรัน"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "สร้างไฟล์งานเพื่อให้ผู้ใช้ดาวน์โหลด",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "ชื่อไฟล์ เช่น script.py, index.html"},
                    "content": {"type": "string", "description": "เนื้อหาในไฟล์"}
                },
                "required": ["filename", "content"]
            }
        }
    }
]

# แสดงประวัติแชทบนหน้าจอหลัก
for msg in st.session_state.messages:
    if msg["role"] not in ["system", "tool"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ----------------------------------------
# 6. ระบบรับข้อความและประมวลผล
# ----------------------------------------
if prompt := st.chat_input(f"กำลังคุยกับ {selected_model} พิมพ์คำสั่งของคุณที่นี่..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status = st.empty()
        status.info(f"กำลังส่งข้อมูลไปที่ {active_config['base_url']} ...")
        
        try:
            response = client.chat.completions.create(
                model=selected_model,
                messages=st.session_state.messages,
                tools=tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            st.session_state.messages.append(message)
            
            # หาก AI เลือกใช้ Tools
            while message.tool_calls:
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                    
                    if function_name == "run_terminal":
                        cmd = arguments.get("command", "")
                        st.code(f"$ {cmd}", language="bash")
                        try:
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                            output = result.stdout if result.stdout else result.stderr
                            if not output: output = "Command executed successfully with no output."
                        except Exception as e:
                            output = str(e)
                            
                        st.session_state.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": output
                        })
                        
                    elif function_name == "create_file":
                        filename = arguments.get("filename", "output.txt")
                        content = arguments.get("content", "")
                        
                        # เซฟไฟล์จริงลงใน Workspace
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(content)
                        st.session_state.downloadable_files[filename] = content
                        st.success(f"📁 สร้างไฟล์ {filename} เรียบร้อยแล้ว (โหลดได้ที่เมนูซ้ายมือ)")
                        
                        st.session_state.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": f"File {filename} created on disk."
                        })
                
                # ส่งผลลัพธ์กลับไปให้ AI คิดต่อ
                status.info("กำลังวิเคราะห์ผลลัพธ์จากระบบ...")
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=st.session_state.messages,
                    tools=tools,
                    tool_choice="auto"
                )
                message = response.choices[0].message
                st.session_state.messages.append(message)
            
            # พิมพ์คำตอบสุดท้ายของ AI
            status.empty()
            if message.content:
                st.markdown(message.content)
        
        except Exception as e:
            status.error(f"เกิดข้อผิดพลาด: {str(e)}")
            st.error("ตรวจสอบว่า API Key, Base URL หรือ Model ID ถูกต้องหรือไม่")
