"use strict";

/**
 * Description
 * @authors Amos Amissah (theonlyamos@gmail.com)
 * @date    2023-12-02 16:25:28
 * @version 1.0.0
 */


class Github{
    static repos;
    static branches;
    static reposElem;
    static submitBtn;
    static projectName;
    static selectedRepo;
    static branchesElem;
    static branchesParentElem;
    static projectDescription;

    constructor(){}

    static init(options){
        this.reposElem = document.getElementById(options.repos)
        this.projectName = document.getElementById(options.name)
        this.submitBtn = document.getElementById(options.submitBtn)
        this.branchesElem = document.getElementById(options.branches)
        this.projectDescription = document.getElementById(options.description)
        this.branchesParentElem = document.getElementById(options.branchesParent)
        
        this.reposElem.onchange = (e)=>{
            this.getRepos(e.target.value)
        }
        this.getRepos()
    }

    static async getRepos(repo_name = null){
        this.setLoading(true)
        let url = '/github/repos'
        url = repo_name ? url + `/${repo_name}` : url
        
        const request = await fetch(url)
        const response = await request.json()

        const {status, message, data} = response
        this.setLoading(false)
        status === 'success' 
        ? repo_name
        ? this.setRepo(data[0])
        : this.setRepos(data)
        : message === 'Expired access tokens'
        ? window.location.reload()
        : console.error(message)
    }

    static setRepos(repos = []){
        this.repos = repos
        repos.forEach((repo)=>{
            let option = document.createElement('option')
            option.value = repo.name
            option.textContent = repo.name
            this.reposElem.appendChild(option)
        })
    }

    static async setRepo(repo = {}){
        this.selectedRepo = repo
        
        if (Object.keys(repo).length){
            this.projectName.value = repo.name
            this.projectDescription.value = repo.description

            this.branchesElem.innerHTML = ''
            this.branchesElem.appendChild(document.createElement('option'))
            repo.branches.forEach((branch)=>{
                let option = document.createElement('option')
                option.value = branch
                option.textContent = branch
                this.branchesElem.appendChild(option)
            })
            this.branchesElem.setAttribute('required', 'required')
            this.branchesParentElem.classList.remove('d-none')
        }
    }

    static setLoading(loading = false){
        if (loading) {
            this.submitBtn.classList.add('disabled')
            document.querySelector('.fa-spinner').classList.remove('d-none')
        }
        else {
            this.submitBtn.classList.remove('disabled')
            document.querySelector('.fa-spinner').classList.add('d-none')
        }
            
    }
}

window.onload = (e)=>{
    Github.init({
        name: 'name',
        repos: 'github_repo',
        description: 'description',
        branches: 'github_repo_branch',
        branchesParent: 'branches_elem',
        submitBtn: 'submitBtn'
    })
}