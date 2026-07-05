from app import create_app

app = create_app()

if __name__ == "__main__":
    # DEPLOYMENT NOTE: host="0.0.0.0" lets other devices on the same
    # school LAN reach this server (e.g. http://<server-ip>:5000) even
    # with no internet connection. See README.md "Deployment model".
    app.run(host="0.0.0.0", port=5000, debug=True)
