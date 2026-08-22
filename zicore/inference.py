class ZiCoreInference:
    """Bridge de inferencia entre los motores A/B y el dashboard"""
    
    def __init__(self):
        self.pipeline_url = "http://localhost:4080/api/infer"
        self.history = []
    
    async def query(self, module: str, instruction: str, input_data: str = "") -> dict:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.pipeline_url, json={
                "module": module,
                "instruction": instruction,
                "input_data": input_data,
            })
            result = resp.json()
            self.history.append({
                "module": module,
                "instruction": instruction,
                "result": result,
            })
            return result
    
    def get_history(self, n: int = 10) -> list:
        return self.history[-n:]
