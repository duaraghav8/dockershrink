from app.service.dockerfile import shell_command as sc

inputs = [
    'mkdir test_dir && cd test_dir || echo "Failed to create or enter directory" ; rm -r test_dir',
    'cat file.txt | grep "error" && echo "Errors found" > log.txt || echo "No errors found"',
    'sleep 5 & echo "Waited for 5 seconds" && echo "Continuing execution" || echo "Error"',
    'echo "Part 1"; echo "Part 2 && Part 3" || echo "Failed" && echo "Done"',
    'echo \'Nested "quotes" here\' && echo "Another \'nested\' string" || echo "Fallback" ; echo \'Done\'',
    'ls -l | grep "myfile" && echo "Found file" > result.txt || echo "File not found" >> error.log',
    'echo "Hello World"',
    '    echo "Command with extra spaces"   &&  ls   -al    ||     echo "Another"',
    'touch \'file;name.txt\' && echo "file created" || echo "failed"',
    'find . -name "*.py" | xargs grep "TODO" & echo "Background search running" > search.log',
]

outputs = [sc.split_chained_commands(i) for i in inputs]

for o in outputs: print(o)

