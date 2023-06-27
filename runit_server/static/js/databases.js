"use strict"

const uid = ()=>{
    let a = new Uint32Array(3);
    window.crypto.getRandomValues(a);
    return (performance.now().toString(36)+Array.from(a).map(A => A.toString(36)).join("")).replace(/\./g,"");
}

const updateSchemas = ()=>{
    let form = document.querySelector('.schema-form')
    if (form.reportValidity()){
        form.submit()
    }
    
}

const deleteElem = (id)=>{
    let elem = document.getElementById(id)
    elem.remove()
}

const setSchemaKey = (elem)=>{
    let name = elem.value
    let id = elem.getAttribute('data-name')
    let schemaTypeSelect = document.getElementById(id)
    schemaTypeSelect.setAttribute('name', name)
}

const createSchema = ()=>{
    let form = document.querySelector('.schema-form')
    
    let formGroup = document.createElement('div')
    formGroup.classList.add('form-group', 'row', 'align-items-center', 'mb-2')
    let id = uid()
    formGroup.id = id

    let firstCol = document.createElement('div')
    let secCol = document.createElement('div')
    let thirdCold = document.createElement('div')
    let fourthCol = document.createElement('div')

    firstCol.classList.add('col-5')
    secCol.classList.add('col-1', 'text-center')
    thirdCold.classList.add('col-5')
    fourthCol.classList.add('col-1')

    let schemaNameInput = document.createElement('input')
    schemaNameInput.setAttribute('type', 'text')
    schemaNameInput.setAttribute('required', 'required')
    schemaNameInput.setAttribute('placeholder', 'Key')
    schemaNameInput.classList.add('form-control', 'form-control-sm')

    let schemaTypes = {'String': 'str', 'Integer': 'int',
                       'Float': 'float', 'Boolean': 'bool',
                       'Text': 'text'}

    let schemaTypeSelect = document.createElement('select')
    schemaTypeSelect.setAttribute('required', 'required')
    schemaTypeSelect.classList.add('form-select-sm', 'w-100')

    let option = document.createElement('option')
    option.setAttribute('disabled', 'disabled')
    option.setAttribute('selected', 'selected')
    option.textContent = 'Type'
    schemaTypeSelect.appendChild(option)
    for (let schemaType in schemaTypes){
        option = document.createElement('option')
        option.setAttribute('value', schemaTypes[schemaType])
        option.textContent = schemaType
        schemaTypeSelect.appendChild(option)
    }

    schemaNameInput.addEventListener('keydown', e => {
        const regex = /[^A-Za-z0-9]/g
        if (e.key.replace(regex, '') && e.key.length == 1){
            schemaTypeSelect.setAttribute('name', schemaNameInput.value + e.key)
        }
    })

    firstCol.appendChild(schemaNameInput)
    secCol.innerHTML = `<span>=</span>`
    thirdCold.appendChild(schemaTypeSelect)
    fourthCol.innerHTML = `<a href="javascript: deleteElem('${id}')" class="nav-link">
                            <i class="fas fa-trash-alt"></i>
                           </a>`

    formGroup.appendChild(firstCol)
    formGroup.appendChild(secCol)
    formGroup.appendChild(thirdCold)
    formGroup.appendChild(fourthCol)
    
    form.appendChild(formGroup)
    
}

window.addEventListener('load', ()=>{
    
})