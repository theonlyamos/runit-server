/**
 * Description
 * @authors Amos Amissah (theonlyamos@gmail.com)
 * @date    2022-08-06 13:48:51
 * @version 1.0.0
 */

const DB_PORTS = {'mysql': 33060, 'mongodb': 27017}

class SetupWizard {
    static form;
    static containerElem;
    static children = [];

    static backBtn;
    static nextBtn;
    static submitBtn;

    static currentIndex = 1;
    static currentStep;

    constructor(){}

    static init(options){
        SetupWizard.form = document.getElementById(options.form)
        SetupWizard.containerElem = document.getElementById(options.parent)
        SetupWizard.children = document.getElementsByClassName(options.children)

        SetupWizard.backBtn = document.getElementById(options.backBtnId)
        SetupWizard.nextBtn = document.getElementById(options.nextBtnId)
        SetupWizard.submitBtn = document.getElementById(options.submitBtnId)

        SetupWizard.actionButtons();

        SetupWizard.hideSteps()
        SetupWizard.showStep(1)
    }

    static actionButtons(){
        SetupWizard.backBtn.addEventListener('click', (e)=>{
            SetupWizard.showPreviousStep()
        })

        SetupWizard.nextBtn.addEventListener('click', (e)=>{
            SetupWizard.showNextStep()
        })

        SetupWizard.submitBtn.addEventListener('click', (e)=>{
            SetupWizard.submitForm()
        })

        SetupWizard.disableBackButton()
    }

    static hideSteps(){
        if (SetupWizard.children.length > 0){
            for (let i = 0; i < SetupWizard.children.length; i++){
                SetupWizard.children[i].classList.add('d-none')
            }
        }
    }

    static disableBackButton(){
        SetupWizard.backBtn.setAttribute('disabled', 'disabled')
        SetupWizard.backBtn.classList.add('text-black-50')
    }

    static enableBackButton(){
        SetupWizard.backBtn.removeAttribute('disabled')
        SetupWizard.backBtn.classList.remove('text-black-50')
    }

    static disableNextButton(){
        SetupWizard.nextBtn.classList.add('d-none')
    }

    static enableNextButton(){
        SetupWizard.nextBtn.classList.remove('d-none')
    }

    static disableSubmitButton(){
        SetupWizard.submitBtn.classList.add('d-none')
    }

    static enableSubmitButton(){
        SetupWizard.submitBtn.classList.remove('d-none')
    }

    static showNextStep(){
        SetupWizard.hideSteps()
        SetupWizard.showStep()
        

        if (SetupWizard.currentIndex > SetupWizard.children.length){
            SetupWizard.disableNextButton()
            SetupWizard.enableSubmitButton()
        }
    }

    static showPreviousStep(){
        SetupWizard.currentIndex -= 2
        SetupWizard.hideSteps()
        SetupWizard.showStep()

        if (SetupWizard.currentIndex <= SetupWizard.children.length){
            SetupWizard.disableSubmitButton()
            SetupWizard.enableNextButton()
        }
    }

    static showStep(){
        SetupWizard.currentStep = SetupWizard.children[SetupWizard.currentIndex-1]
        SetupWizard.currentStep.classList.remove('d-none')

        if (SetupWizard.currentIndex > 1){
            SetupWizard.enableBackButton()
        }
        else {
            SetupWizard.disableBackButton()
        }

        SetupWizard.currentIndex += 1
    }

    static validateForm(){
        return SetupWizard.form.reportValidity();
    }

    static submitForm(){
        if (SetupWizard.validateForm()){
            SetupWizard.form.submit();
        }
    }
}

const selectDMEngine = (value)=>{
    document.querySelector("[name='dbport']").value = DB_PORTS[value]
}

window.onload = (e)=>{
    SetupWizard.init({
        form: 'setupForm',
        parent: 'setupWizard',
        children: 'setup-step',
        backBtnId: 'setupBackButton',
        nextBtnId: 'setupNextButton',
        submitBtnId: 'setupSubmitButton'
    })
}
