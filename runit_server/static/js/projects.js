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

const setLoading = (loading = false) => {
    let submitBtn = document.getElementById('submitBtn')
    if (loading) {
        submitBtn.classList.add('disabled')
        document.querySelector('.fa-spinner').classList.remove('d-none')
    }
    else {
        submitBtn.classList.remove('disabled')
        document.querySelector('.fa-spinner').classList.add('d-none')
    } 
}

class Project{

    constructor(project_data = {}){
        for (let key in project_data){
            this.__proto__[key] = project_data[key]
        }
    }

    static async get(project_id = null){
        if (!project_id) return null
        let access_token = document.getElementById('accessToken').innerText.trim()
        
        // setLoading(true)
        let url = `/api/v1/projects/${project_id}`

        let response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${access_token}`
            }
        })

        let result = await response.json()
        
        return new Project(result)
    }

    static async create(form){
        if (!form.reportValidity()) return null

        setLoading(true)
        let data = Object.fromEntries(new FormData(form))
        let access_token = document.getElementById('accessToken').innerText.trim()
        let modalCloseBtn = document.querySelector('.btn-close')

        let url =  '/api/v1/projects/'

        let response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${access_token}`
            },
            method: 'POST',
            mode: 'same-origin',
            body: JSON.stringify(data)
        })

        let result = await response.json()
  
        setLoading(false)
        
        const {status, message, project} = result
        
        if (status === 'success'){
            console.log(message)
            console.log(project)
            modalCloseBtn.click()
            return new Project(project)
        }
        console.error(message)
        return null

        
    }

    static setRepos(repos = []){

    }

    static async setRepo(repo = {}){

    }

    
}

window.onload = async(e)=>{
    let url_parts = window.location.pathname.split('/')
    console.log(url_parts)
    if (url_parts.length >= 3 && url_parts[1] === 'projects') {
        let project_id = url_parts[2]
        let project = await Project.get(project_id)
    }

    let projectForm = document.getElementById('projectForm')
    console.log(projectForm)
    if (projectForm){
        projectForm.onsubmit = (e)=>{
            e.preventDefault()

            Project.create(projectForm)
        }
    }
}