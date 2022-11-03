exports.index = ()=>{
    console.log('Yay, Javascript works!!!')
}

exports.counter = ()=>{
    console.log(1,2,3,4,5)
}

exports.printout = (string)=>{
    console.log(string)
}

exports.gettime = ()=>{
    console.log(new Date().toUTCString())
}

exports.html = ()=>{
    const fs = require('fs')
    console.log(fs.readFileSync('index.html', {encoding: 'utf-8'}))
}