from app.models.execution import ExecutionRequest


OUTPUT_OBSERVATION_MARKER = "# --- RUN & OUTPUT：印出結果 ---"


def normalize_execution_request(request: ExecutionRequest) -> ExecutionRequest:
    """Keep learner code and post-check observation code in separate phases."""
    marker_index = request.code.rfind(OUTPUT_OBSERVATION_MARKER)
    if marker_index == -1:
        return request

    code = request.code[:marker_index].rstrip()
    embedded_observation = request.code[marker_index + len(OUTPUT_OBSERVATION_MARKER):].strip()
    return request.model_copy(update={
        "code": f"{code}\n",
        "observation_code": embedded_observation or request.observation_code,
    })
