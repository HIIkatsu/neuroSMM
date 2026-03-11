
const tg=window.Telegram.WebApp

tg.expand()

const screen=document.getElementById("screen")

function home(){

screen.innerHTML=`
<div class="card">
Welcome to NeuroSMM panel
</div>
`

}

async function drafts(){

let data=await api("/drafts")

let html=""

for(let d of data){

html+=`<div class="card">${d.text}</div>`

}

screen.innerHTML=html

}

function editor(){

screen.innerHTML=`

<div class="card">

<textarea id="text"></textarea>

<button onclick="createDraft()">Save draft</button>

</div>

`

}

async function createDraft(){

let text=document.getElementById("text").value

await api("/drafts/create","POST",{text})

drafts()

}

async function plan(){

let data=await api("/plan")

let html=`<button onclick="generatePlan()">Generate 30 day plan</button>`

for(let p of data){

html+=`

<div class="card">

<b>${p.date}</b><br>

${p.topic}

</div>

`

}

screen.innerHTML=html

}

async function generatePlan(){

await api("/plan/generate","POST",{days:30})

plan()

}

async function channels(){

let data=await api("/channels")

let html=""

for(let c of data){

html+=`

<div class="card">

${c.name}

<button onclick="selectChannel(${c.id})">Select</button>

</div>

`

}

screen.innerHTML=html

}

async function selectChannel(id){

await api("/channels/select","POST",{channel_id:id})

alert("Channel selected")

}

home()
