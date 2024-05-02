class Alert {
    
    STATUS_MAPPING = {
        success: 'success',
        warning: 'warning',
        error: 'danger',
        log: 'info'
    }

    constructor(status, message){
        this.status = status
        this.message = message

        this.initialize()
    }

    initialize(){
        let container = document.createElement('div')
        container.classList.add('custom-alert', 'px-2', 'py-1',)
        container.classList.add(`text-bg-${this.STATUS_MAPPING[this.status]}`)
        container.classList.add('position-absolute', 'd-flex', 'shadow')
        container.classList.add('align-items-center', 'justify-content-between')
        container.style.minWidth = '250px'
        container.style.top = '10px'
        container.style.right = '10px'
        container.style.zIndex = '999'

        let msgElem = document.createElement('small')
        msgElem.textContent = this.message

        let closeBtn = document.createElement('i')
        closeBtn.classList.add('fas', 'fa-times', 'cursor-pointer')

        closeBtn.onclick = (e)=>{
            container.style.right = '-300px';
            container.remove()
        }

        container.appendChild(msgElem)
        container.appendChild(closeBtn)
        document.body.appendChild(container)

        setTimeout(()=>{
            if (container)
                container.remove()
        }, 5000)
    }

    static success(message){
        new Alert('success', message)
    }

    static warning(message){
        new Alert('warning', message)
    }

    static error(message){
        new Alert('error', message)
    }

    static log(message){
        new Alert('log', message)
    }
}