"use strict";

class FileBrowser {
    static #EXTENSION_TO_LANGUAGE = {
        'py': 'python', 'pyw': 'python','php': 'php',
        'js': 'javascript', 'jsx': 'javascript',
        'ts': 'javascript', 'tsx': 'javascript',
        'cjs': 'javascript', 'mjs': 'javascript',
        'json': 'javascript', 'html': 'html',
        'css': 'css', 'scss': 'css', 'less': 'css'
    }

    static #container = document.querySelector('#directory');
    static #project = {};
    static #saveBtn = document.querySelector("#saveBtn");
    static #closeBtn = document.querySelector("#closeBtn");
    static #themeSelector = document.querySelector("#themes");
    static editoropened = false;
    static editor = {};
    static files = [];
    static selected = null;
    static curdir = '.'

    constructor(){ }

    static async openFile(filename){
        
        const fileParts = filename.split('.')
        const extension = fileParts[fileParts.length-1]
        const language = FileBrowser.#EXTENSION_TO_LANGUAGE[extension] || 'text'
        FileBrowser.editor.session.setMode(`ace/mode/${language}`);
        
        FileBrowser.selected = filename

        let url = `${location.origin}/projects/editor/${FileBrowser.#project.id}/`
        url += `?file=${FileBrowser.selected}`

        const request = await fetch(url)
        const response = await request.json()
        const {content, status, message} = response
        
        status === 'success' 
        ? FileBrowser.editor.setValue(content)
        : console.log(message)

        FileBrowser.editoropened = true;
        FileBrowser.#saveBtn.classList.remove('d-none')
    }

    static openFolder(files=[]){
        FileBrowser.files = files
        FileBrowser.#container.innerHTML = ''

        for (let i = 0; i < files.length; i++){
            const file = files[i]
            const fileNode = document.createElement('div')
            fileNode.onclick = (e =>{
                FileBrowser.openFile(file['name'])
            })
            fileNode.classList.add('files-container')
            fileNode.innerHTML += file['isfile'] ? `-` : `+`
            fileNode.innerHTML += `<span class="ps-1">${file['name']}</span>`
            FileBrowser.#container.appendChild(fileNode)
        }
    }

    static setProject(project){
        FileBrowser.#project = project
    }

    static loadEditor(editor){
        FileBrowser.editor = editor
        FileBrowser.editor.setTheme("ace/theme/monokai");
        
        FileBrowser.editor.commands.addCommand({
            name: 'Save',
            bindKey: {win: 'Ctrl-S',  mac: 'Command-S'},
            exec: FileBrowser.saveFile,
            readOnly: true,
        });
        
        FileBrowser.#saveBtn.onclick = (e =>{
            FileBrowser.saveFile()
        })
        FileBrowser.#closeBtn.onclick = (e =>{
            FileBrowser.editoropened = false;
        })
        FileBrowser.#themeSelector.onchange = (e => {
            FileBrowser.editor.setTheme(`ace/theme/${e.target.value}`);
        })
    }

    static async saveFile(editor=null){
        let data = FileBrowser.editor.getValue()

        try {
            let url = `${location.origin}/projects/editor/${FileBrowser.#project.id}/`
            url += `?file=${FileBrowser.selected}`

            const response = await fetch(url, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({data}),
            });

            const result = await response.json()
            const {status, message} = result
            
            status !== 'success' 
            ? console.log(message)
            : console.error(message);

        } catch (error) {
            console.log(error.message)
        }
        
    }
}

const getProject = async()=>{
    return new Promise(async(resolve, reject)=>{
        try {
            const urlParts = location.href.split("/")
            const projectID = urlParts[4]
            const url = `${location.origin}/projects/files/${projectID}/`
    
            const request = await fetch(url)
            const response = await request.json()
            const {files, project, status, message} = response
            
            status === 'success' 
            ? resolve({files, project})
            : reject(new Error(message))
        } catch (error) {
            console.log(error);
            reject(error?.message)
        }
        
    })
}

window.onload = (async(e) =>{
    const {project, files} = await getProject()
    FileBrowser.setProject(project)
    FileBrowser.openFolder(files)
    const editor = ace.edit("editor");
    FileBrowser.loadEditor(editor)
})

window.onbeforeunload =  ((e)=> {
    if (FileBrowser.editoropened){
        e.preventDefault();
        e.returnValue = '';
    }
});