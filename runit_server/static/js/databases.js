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
    formGroup.classList.add('form-group', 'd-flex', 'align-items-center')
    formGroup.classList.add('justify-content-between', 'gap-3', 'pb-2')
    let id = uid()
    formGroup.id = id

    let schemaNameInput = document.createElement('input')
    schemaNameInput.setAttribute('type', 'text')
    schemaNameInput.setAttribute('required', 'required')
    schemaNameInput.setAttribute('placeholder', 'Key')
    schemaNameInput.classList.add('form-control', 'form-control-sm', 'py-2')
    schemaNameInput.classList.add('border-0', 'bg-light', 'text-secondary', 'hover:shadow-sm')

    let schemaTypes = {'String': 'str', 'Integer': 'int',
                       'Float': 'float', 'Boolean': 'bool',
                       'Text': 'text'}

    let schemaTypeSelect = document.createElement('select')
    schemaTypeSelect.setAttribute('required', 'required')
    schemaTypeSelect.classList.add('form-select', 'form-select-sm', 'py-2')
    schemaTypeSelect.classList.add('border-0', 'bg-light', 'text-secondary', 'hover:shadow-sm')

    let option = document.createElement('option')
    option.setAttribute('disabled', 'disabled')
    option.setAttribute('selected', 'selected')
    option.classList.add('text-secondary')
    option.textContent = 'Type'
    schemaTypeSelect.appendChild(option)
    for (let schemaType in schemaTypes){
        option = document.createElement('option')
        option.setAttribute('value', schemaTypes[schemaType])
        option.classList.add('text-secondary')
        option.textContent = schemaType
        schemaTypeSelect.appendChild(option)
    }

    schemaNameInput.addEventListener('keydown', e => {
        const regex = /[^A-Za-z0-9]/g
        if (e.key.replace(regex, '') && e.key.length == 1){
            schemaTypeSelect.setAttribute('name', schemaNameInput.value + e.key)
        }
    })

    let equalSign = document.createElement('span')
    equalSign.textContent = '='

    let deleteBtn = document.createElement('a')
    deleteBtn.setAttribute('href', `javascript: deleteElem('${id}')`)
    deleteBtn.classList.add('nav-link')
    deleteBtn.innerHTML = `<i class="fas fa-times text-danger"></i>`

    formGroup.appendChild(schemaNameInput)
    formGroup.appendChild(equalSign)
    formGroup.appendChild(schemaTypeSelect)
    formGroup.appendChild(deleteBtn)
    
    form.appendChild(formGroup)
    
}

window.addEventListener('load', ()=>{
    
})