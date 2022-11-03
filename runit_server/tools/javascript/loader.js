try {
    if (process.argv.length > 2) {
        const filename = process.argv[2]
        const methods = require(filename)

        console.log(Object.keys(methods))
    }
} catch (error) {
    console.log(error.toString().split('\n')[0])
}