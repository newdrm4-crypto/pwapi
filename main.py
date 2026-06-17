import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PW Web Player API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/pw", response_class=HTMLResponse)
async def get_player(request: Request):
    # URL se saare parameters nikalna
    url = request.query_params.get("url", "")
    token = request.query_params.get("token", "")

    # Yeh HTML browser mein jayega aur video play karega
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PW Player</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/shaka-player/4.3.5/shaka-player.ui.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/shaka-player/4.3.5/controls.min.css">
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: black;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                overflow: hidden;
            }}
            #video-container {{
                width: 100%;
                height: 100%;
                max-width: 100%;
            }}
            video {{
                width: 100%;
                height: 100%;
            }}
        </style>
    </head>
    <body>
        <div id="video-container" data-shaka-player-container>
            <video id="video" data-shaka-player autoplay></video>
        </div>

        <script>
            const manifestUri = "{url}";
            const token = "{token}";

            async function init() {{
                const video = document.getElementById('video');
                const player = new shaka.Player(video);
                
                const ui = video['ui'];
                const controls = ui.getControls();

                // Video server par request bhejte waqt Token add karna
                player.getNetworkingEngine().registerRequestFilter(function(type, request) {{
                    if (!request.headers) {{
                        request.headers = {{}};
                    }}
                    if (token) {{
                        request.headers['Authorization'] = 'Bearer ' + token;
                    }}
                    request.headers['Origin'] = 'https://www.pw.live';
                    request.headers['Referer'] = 'https://www.pw.live/';
                }});

                try {{
                    await player.load(manifestUri);
                    console.log('Video loaded successfully!');
                }} catch (e) {{
                    console.error('Error loading video:', e);
                    alert("Video load nahi ho payi. Token ya URL check karein.");
                }}
            }}

            // Jab Shaka UI load ho jaye tab init() call karein
            document.addEventListener('shaka-ui-loaded', init);
        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
