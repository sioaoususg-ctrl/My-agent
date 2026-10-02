import streamlit as st
from openai import OpenAI
import subprocess
import json
import os

# ----------------------------------------
# 1. ตั้งค่าหน้าเว็บ UI (ให้ดูสวยงามและกว้าง)
# ----------------------------------------
st.set_page_config(page_title="Ultimate AI Workspace", page_icon="🚀", layout="wide")
st.title("🚀 My Ultimate AI Workspace")
st.markdown("แชท, สั่งงาน Terminal, แนบไฟล์ และสร้างโปรแกรมได้ในที่เดียว (ส่วนตัว 100%)")

# ----------------------------------------
# 2. แถบเครื่องมือด้านข้าง (Sidebar)
# ----------------------------------------
with st.sidebar:
    st.header("⚙️ ตั้งค่า & โมเดล")
    # ผู้ใช้สามารถพิมพ์ชื่อโมเดลเปลี่ยนได้เองเลย
    MODEL = st.text_input("🤖 ชื่อโมเดล (เปลี่ยนได้ตามต้องการ)", value="pp/claude-opus-5.5")
    
    st.markdown("---")
    st.header("📎 แนบไฟล์ให้ AI")
    uploaded_files = st.file_uploader("อัปโหลดไฟล์ (รูป, ข้อความ, โค้ด)", accept_multiple_files=True)
    
    # ถัามีการแนบไฟล์ ให้เซฟลงโฟลเดอร์ปัจจุบันเลย AI จะได้ใช้ Terminal อ่านได้
    if uploaded_files:
        for file in uploaded_files:
            with open(file.name, "wb") as f:
                f.write(file.getbuffer())
        st.success(f"อัปโหลดเข้า Workspace แล้ว {len(uploaded_files)} ไฟล์ (บอกให้ AI ใช้คำสั่ง ls ดูได้เลย)")
    
    st.markdown("---")
    st.header("📥 ไฟล์ที่ AI สร้างให้")
    if "downloadable_files" not in st.session_state:
        st.session_state.downloadable_files = {}
        
    if not st.session_state.downloadable_files:
        st.info("ยังไม่มีไฟล์ที่สร้าง")
    else:
        for fname, fcontent in st.session_state.downloadable_files.items():
            st.download_button(label=f"⬇️ ดาวน์โหลด {fname}", data=fcontent, file_name=fname)

# ----------------------------------------
# 3. ตั้งค่า API และ State การแชท
# ----------------------------------------
client = OpenAI(
    base_url="https://n8n.carwraman.shop/v1",
    api_key="sk-807d1f1ecf22bfa0-80e207-4490935c"
)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "คุณคือ AI Agent ระดับสูง คุณทำงานอยู่บนเครื่องของผู้ใช้ มีสิทธิ์รัน Terminal และสร้างไฟล์ คุณสามารถอ่านไฟล์ที่ผู้ใช้อัปโหลดได้โดยการรันคำสั่ง terminal เช่น cat หรือ python หากผู้ใช้ให้งานมา ให้วิเคราะห์ รันคำสั่ง และสรุปผล หรือสร้างไฟล์ให้"}
    ]

# แสดงประวัติแชท
for msg in st.session_state.messages:
    if msg["role"] not in ["system", "tool"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ----------------------------------------
# 4. ฟังก์ชัน Tools สำหรับ AI
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

# ----------------------------------------
# 5. ระบบรับข้อความและประมวลผล
# ----------------------------------------
if prompt := st.chat_input("พิมพ์คำสั่งของคุณที่นี่... (เช่น 'ช่วยดูไฟล์ที่แนบมาให้หน่อย' หรือ 'เขียนสคริปต์สุ่มเลข')"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status = st.empty()
        status.info("กำลังประมวลผล...")
        
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=st.session_state.messages,
                tools=tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            st.session_state.messages.append(message)
            
            # หาก AI เลือกใช้ Tools (Terminal หรือ สร้างไฟล์)
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
                        # เซฟไฟล์จริงลงใน Workspace และเพิ่มเข้าคิวให้ดาวน์โหลด
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
                    model=MODEL,
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
            status.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ API: {str(e)}")
