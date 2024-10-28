function generateToken() {
    fetch('/api/v1/generate_token', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        alert('New API Token: ' + data.token);
        location.reload();
    });
}

function storeFeedback(event) {
    event.preventDefault();
    const description = document.getElementById('feedback_description').value;
    fetch('/api/v1/feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ feedback_description: description }),
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
    });
}

function storeOpenAIKey(event) {
    event.preventDefault();
    const openai_key = document.getElementById('openai_key').value;
    fetch('/api/v1/store_openai_key', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ openai_key: openai_key }),
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
    });
}
