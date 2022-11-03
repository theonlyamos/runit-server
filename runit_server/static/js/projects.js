"use strict"

const uid = ()=>{
    let a = new Uint32Array(3);
    window.crypto.getRandomValues(a);
    return (performance.now().toString(36)+Array.from(a).map(A => A.toString(36)).join("")).replace(/\./g,"");
}

const updateEnvs = ()=>{
    let form = document.querySelector('.env-form')
    form.submit()
}

const deleteElem = (id)=>{
    let elem = document.getElementById(id)
    elem.remove()
}

const setEnvKey = (elem)=>{
    let name = elem.value
    let id = elem.getAttribute('data-name')
    let envValueInput = document.getElementById(id)
    envValueInput.setAttribute('name', name)
    
}

const createEnv = ()=>{
    let form = document.querySelector('.env-form')
    
    let formGroup = document.createElement('div')
    formGroup.classList.add('form-group', 'row', 'align-items-center', 'mb-2')
    let id = uid()
    formGroup.id = id

    let firstCol = document.createElement('div')
    let secCol = document.createElement('div')
    let thirdCold = document.createElement('div')
    let fourthCol = document.createElement('div')

    firstCol.classList.add('col-5')
    secCol.classList.add('col-1')
    thirdCold.classList.add('col-5')
    fourthCol.classList.add('col-1')

    let envNameInput = document.createElement('input')
    envNameInput.setAttribute('type', 'text')
    envNameInput.setAttribute('required', 'required')
    envNameInput.setAttribute('placeholder', 'Key')
    envNameInput.classList.add('form-control', 'form-control-sm')

    let envValueInput = document.createElement('input')
    envValueInput.setAttribute('type', 'text')
    envValueInput.setAttribute('required', 'required')
    envValueInput.setAttribute('placeholder', 'Value')
    envValueInput.classList.add('form-control', 'form-control-sm')

    envNameInput.addEventListener('keydown', e => {
        const regex = /[^A-Za-z0-9]/g
        if (e.key.replace(regex, '') && e.key.length == 1){
            envValueInput.setAttribute('name', envNameInput.value + e.key)
        }
    })

    firstCol.appendChild(envNameInput)
    secCol.innerHTML = `<span>=</span>`
    thirdCold.appendChild(envValueInput)
    fourthCol.innerHTML = `<a href="javascript: deleteElem('${id}')" class="nav-link">
                            <i class="fas fa-trash-alt"></i>
                           </a>`

    formGroup.appendChild(firstCol)
    formGroup.appendChild(secCol)
    formGroup.appendChild(thirdCold)
    formGroup.appendChild(fourthCol)

    form.prepend(formGroup)
    
}

window.addEventListener('load', ()=>{
    
})