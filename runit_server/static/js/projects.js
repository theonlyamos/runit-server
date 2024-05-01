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
    formGroup.classList.add('form-group', 'd-flex', 'justify-content-between', 'align-items-center', 'gap-3', 'rounded-0', 'pb-2')
    let id = uid()
    formGroup.id = id


    let envNameInput = document.createElement('input')
    envNameInput.setAttribute('type', 'text')
    envNameInput.setAttribute('required', 'required')
    envNameInput.setAttribute('placeholder', 'Key')
    envNameInput.classList.add('form-control', 'form-control-sm', 'key-input', 'rounded-0')

    let envValueInput = document.createElement('input')
    envValueInput.setAttribute('type', 'text')
    envValueInput.setAttribute('required', 'required')
    envValueInput.setAttribute('placeholder', 'Value')
    envValueInput.classList.add('form-control', 'form-control-sm', 'rounded-0')

    envNameInput.addEventListener('keydown', e => {
        const regex = /[^A-Za-z0-9]/g
        if (e.key.replace(regex, '') && e.key.length == 1){
            envValueInput.setAttribute('name', envNameInput.value + e.key)
        }
    })

    let equalSign = document.createElement('span')
    equalSign.innerText = '='
    
    let deleteBtn = document.createElement('a')
    deleteBtn.setAttribute('href', `javascript: deleteElem('${id}')`)
    deleteBtn.classList.add('nav-link')
    deleteBtn.innerHTML = `<i class="fas fa-times text-danger"></i>`

    formGroup.appendChild(envNameInput)
    formGroup.appendChild(equalSign)
    formGroup.appendChild(envValueInput)
    formGroup.appendChild(deleteBtn)

    form.append(formGroup)
    
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

        try {
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
                // modalCloseBtn.click()
                window.location.reload()
                // return new Project(project)
            }
            console.error(message)
            return null
            
        } catch (error) {
            setLoading(false)
            console.log(error)
        }


        
    }

    static setRepos(repos = []){

    }

    static async setRepo(repo = {}){

    }

    
}

window.onload = async(e)=>{
    if (window.location.pathname === '/projects/'){
        let selectAll = document.getElementById('selectAll')
        let allChecks = document.querySelectorAll('[type=checkbox]:not(#selectAll)')

        if (selectAll){ 
            selectAll.onchange = ((e)=>{
                allChecks.forEach((checker)=>{
                    checker.checked = selectAll.checked
                })
            })
        }
        const confirmModal = document.getElementById('confirmModal')
        confirmModal.addEventListener('show.bs.modal', event => {
            let selected = document.querySelectorAll('[type=checkbox]:checked:not(#selectAll)')
            if (!selected.length){
                event.preventDefault()
            }
            let projectIds = []
            let projectNames = []

            selected.forEach(checkbox => {
                let projectId = checkbox.dataset.projectId;
                let projectName = checkbox.dataset.projectName;
                if (projectId && projectName) {
                    projectIds.push(projectId);
                    projectNames.push(projectName);
                }
            });
            let confirmElem = document.getElementById('confirmationMessage')

            if (confirmElem){
                let count = projectNames.length
                confirmElem.innerText = `Are you sure you want to delete ${count > 1 ? 'these' : 'this'} project${count > 1 ? 's' : ''}: [${projectNames}]?`
            }
        })
        Github.init({
            name: 'name',
            repos: 'github_repo',
            description: 'description',
            branches: 'github_repo_branch',
            branchesParent: 'branches_elem',
            submitBtn: 'submitBtn'
        })
    }

    let url_parts = window.location.pathname.split('/')
    
    if (url_parts.length >= 3 && url_parts[1] === 'projects') {
        let project_id = url_parts[2]
        let project = await Project.get(project_id)
    }

    let projectForm = document.getElementById('projectForm')
    
    if (projectForm){
        projectForm.onsubmit = (e)=>{
            e.preventDefault()

            Project.create(projectForm)
        }
    }
}