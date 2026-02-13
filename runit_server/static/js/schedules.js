function loadProjectFunctions(projectId) {
    const functionSelect = document.getElementById('function-name');
    functionSelect.innerHTML = '<option value="">Loading...</option>';
    
    fetch(`/schedules/functions/${projectId}`)
        .then(r => r.json())
        .then(data => {
            functionSelect.innerHTML = '<option value="">Select a function</option>';
            if (data.success && data.functions) {
                data.functions.forEach(func => {
                    const option = document.createElement('option');
                    option.value = func;
                    option.textContent = func;
                    functionSelect.appendChild(option);
                });
            } else {
                functionSelect.innerHTML = '<option value="">No functions found</option>';
            }
        })
        .catch(err => {
            console.error('Error loading functions:', err);
            functionSelect.innerHTML = '<option value="">Error loading functions</option>';
        });
}

function setCronFromPreset(expression) {
    if (expression) {
        document.getElementById('cron-expression').value = expression;
    }
}

function saveSchedule() {
    const form = document.getElementById('schedule-form');
    const formData = new FormData(form);
    const btn = event.currentTarget;
    const originalText = btn.innerHTML;
    const scheduleId = formData.get('schedule_id');
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin fa-fw me-1"></i> Saving...';
    btn.disabled = true;
    
    const url = scheduleId ? `/schedules/${scheduleId}` : '/schedules';
    
    fetch(url, {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert(data.message || 'Failed to save schedule');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        alert('An error occurred');
    })
    .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

function toggleSchedule(scheduleId) {
    fetch(`/schedules/${scheduleId}/toggle`, {
        method: 'POST'
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert(data.message || 'Failed to toggle schedule');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        alert('An error occurred');
    });
}

function deleteSchedule(scheduleId) {
    if (!confirm('Are you sure you want to delete this schedule?')) {
        return;
    }
    
    fetch(`/schedules/${scheduleId}/delete`, {
        method: 'POST'
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/schedules';
        } else {
            alert(data.message || 'Failed to delete schedule');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        alert('An error occurred');
    });
}

function editSchedule(scheduleId) {
    window.location.href = `/schedules/${scheduleId}`;
}
