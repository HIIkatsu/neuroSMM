
const API="/api"

async function api(path,method="GET",data=null){

let opts={method}

if(data){

opts.headers={"Content-Type":"application/json"}
opts.body=JSON.stringify(data)

}

let r=await fetch(API+path,opts)
return r.json()

}
