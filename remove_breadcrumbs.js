const fs = require('fs');
const path = require('path');

function walk(dir) {
    let results = [];
    const list = fs.readdirSync(dir);
    list.forEach(function(file) {
        file = path.join(dir, file);
        const stat = fs.statSync(file);
        if (stat && stat.isDirectory()) { 
            results = results.concat(walk(file));
        } else if (file.endsWith('.tsx')) {
            results.push(file);
        }
    });
    return results;
}

const files = walk('apps/web/src/app/(dashboard)/agricola/safras/[id]');
let modified = 0;

files.forEach(file => {
    let content = fs.readFileSync(file, 'utf8');
    
    // Simple regex to remove breadcrumbs={[ ... ]} from PageHeader
    const regex = /\s*breadcrumbs=\{\[[\s\S]*?\]\}/g;
    
    if (regex.test(content)) {
        content = content.replace(regex, '');
        fs.writeFileSync(file, content, 'utf8');
        modified++;
        console.log(`Modified ${file}`);
    }
});

console.log(`Finished. Modified ${modified} files.`);
