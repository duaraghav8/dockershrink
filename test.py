import bashlex

code = """
if [ "$1" = "hello" ]; then
    echo "Greetings!"
else
    echo "No greeting provided."
fi
"""

tree = bashlex.parsesingle(code)
print(tree.kind)

code = """
for i in 1 2 3; do
    echo "for loop iteration: $i"
done
"""

tree = bashlex.parsesingle(code)
print(tree.kind)

code = """
while [ $COUNTER -lt 3 ]; do
    echo "while loop iteration: $COUNTER"
    ((COUNTER++))
done
"""

tree = bashlex.parsesingle(code)
print(tree.kind)

code = """
until [ $COUNTER2 -eq 0 ]; do
    echo "until loop iteration: $COUNTER2"
    ((COUNTER2--))
done
"""

tree = bashlex.parsesingle(code)
print(tree.kind)
