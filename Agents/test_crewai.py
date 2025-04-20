from crewai import Task
import inspect

print("Task class init parameters:")
try:
    # Get the signature of the Task class constructor
    signature = inspect.signature(Task.__init__)
    print(signature)
except Exception as e:
    print(f"Error getting signature: {e}")

# Create a simple task to see the attributes
try:
    task = Task(
        description="Test task",
        expected_output="Test output"
    )
    print("\nTask object attributes:")
    print(vars(task))
    
    print("\nTask class available methods:")
    methods = [method for method in dir(Task) if not method.startswith('_')]
    print(methods)
    
    print("\nTrying different context formats:")
    
    # Try with list of tasks
    print("\nList of tasks as context:")
    try:
        context_task1 = Task(
            description="Context task 1",
            expected_output="Context output 1"
        )
        context_task2 = Task(
            description="Context task 2",
            expected_output="Context output 2"
        )
        
        task_with_task_context = Task(
            description="Main task with task context",
            expected_output="Main output",
            context=[context_task1, context_task2]
        )
        print("Success with list of tasks context")
        print(vars(task_with_task_context)["context"])
    except Exception as e:
        print(f"Error with list of tasks context: {e}")
        
    # Try with raw strings in list
    print("\nList of strings as context:")
    try:
        string_list_context_task = Task(
            description="Task with string list context",
            expected_output="String list output",
            context=["String 1", "String 2"]
        )
        print("Success with list of strings context")
        print(vars(string_list_context_task)["context"])
    except Exception as e:
        print(f"Error with list of strings context: {e}")

except Exception as e:
    print(f"Error creating task: {e}") 