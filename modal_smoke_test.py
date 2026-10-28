import modal

app = modal.App("si-orbit-smoke-test")


@app.function()
def check_connection():
    return {
        "project": "SI ORBIT",
        "status": "connected",
        "purpose": "Verify Modal serverless execution",
    }


@app.local_entrypoint()
def main():
    result = check_connection.remote()
    print(result)
