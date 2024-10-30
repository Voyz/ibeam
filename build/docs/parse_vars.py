import ast
import re
import sys

def parse_var_py(lines):
    variables = []
    current_section = ''
    section_pattern = re.compile(r'#+\s*(.*?)\s*#+')
    assign_start_pattern = re.compile(r'^(\w+)\s*=')
    i = 0
    total_lines = len(lines)
    while i < total_lines:
        line = lines[i]
        stripped_line = line.strip()
        # Check for section header
        section_match = section_pattern.match(stripped_line)
        if section_match:
            current_section = section_match.group(1).strip()
            i += 1
            continue
        # Check for variable assignment start
        assign_match = assign_start_pattern.match(stripped_line)
        if assign_match:
            # Collect lines until the assignment ends
            assign_lines = [line]
            paren_balance = line.count('(') - line.count(')')
            i += 1
            while paren_balance > 0 and i < total_lines:
                line = lines[i]
                assign_lines.append(line)
                paren_balance += line.count('(') - line.count(')')
                i += 1
            # Now we have the full assignment
            assign_text = ''.join(assign_lines)
            result = parse_assignment(assign_text)
            if result:
                var_name, env_var_name, default_value = result
                # Now check if the next line is a docstring
                docstring = ''
                if i < total_lines:
                    next_line = lines[i].strip()
                    if next_line.startswith('"""'):
                        docstring_lines = []
                        while i < total_lines:
                            line = lines[i].rstrip('\n')
                            docstring_lines.append(line)
                            if line.strip().endswith('"""') and len(line.strip()) > 3:
                                break
                            i += 1
                        docstring = '\n'.join(docstring_lines)
                        # Remove triple quotes
                        docstring = docstring.strip('"""').strip()
                        i += 1
                variables.append({
                    'section': current_section,
                    'var_name': env_var_name,
                    'default_value': default_value.strip().strip('"\''),
                    'description': docstring.strip(),
                })
            else:
                i += 1  # Move to the next line if parsing failed
        else:
            i += 1
    return variables

def parse_assignment(assign_text):
    try:
        assign_node = ast.parse(assign_text)
        if len(assign_node.body) != 1 or not isinstance(assign_node.body[0], ast.Assign):
            return None
        assign = assign_node.body[0]
        var_name = assign.targets[0].id
        value_node = assign.value

        # Now we need to find the os.environ.get() call in value_node
        # This might be directly in value_node, or nested inside function calls

        def find_environ_get_call(node):
            if isinstance(node, ast.Call):
                # Check if this is a call to os.environ.get
                func = node.func
                if (isinstance(func, ast.Attribute) and
                        isinstance(func.value, ast.Attribute) and
                        isinstance(func.value.value, ast.Name) and
                        func.value.value.id == 'os' and
                        func.value.attr == 'environ' and
                        func.attr == 'get'):
                    return node  # Found the os.environ.get() call
                else:
                    # Recursively search in the function and arguments
                    result = find_environ_get_call(node.func)
                    if result:
                        return result
                    for arg in node.args:
                        result = find_environ_get_call(arg)
                        if result:
                            return result
            elif isinstance(node, ast.Attribute):
                return None
            else:
                for child in ast.iter_child_nodes(node):
                    result = find_environ_get_call(child)
                    if result:
                        return result
            return None

        environ_get_call = find_environ_get_call(value_node)
        if environ_get_call:
            args = environ_get_call.args
            if len(args) >= 1:
                env_var_name_node = args[0]
                if isinstance(env_var_name_node, ast.Constant):
                    env_var_name = env_var_name_node.value
                else:
                    return None
                if len(args) >= 2:
                    default_value_node = args[1]
                    # Reconstruct the default value expression
                    if sys.version_info >= (3, 9):
                        default_value = ast.unparse(default_value_node).strip()
                    else:
                        import astor
                        default_value = astor.to_source(default_value_node).strip()
                else:
                    default_value = 'None'
                return var_name, env_var_name, default_value
        else:
            return None
    except Exception as e:
        return None

def camel_case(s):
    s2 = re.sub(r'[^a-zA-Z0-9\- ]', '', s)
    return ' '.join(word.capitalize() for word in s2.split())

def generate_markdown(variables):
    from collections import defaultdict

    sections = defaultdict(list)
    for var in variables:
        sections[var['section']].append(var)

    markdown = ''
    for section, vars_in_section in sections.items():
        if section:
            # Generate anchor name
            anchor_name = section.lower().replace('#', '').strip().replace(' ', '-')
            # Convert section title to CamelCase
            section_title = camel_case(section.replace('#', '').strip())
            markdown += f"\n#### <a name=\"{anchor_name}\"></a>{section_title} \n\n"
        markdown += "| Variable name | Default value | Description |\n"
        markdown += "| ---  | ----- | --- |\n"
        for var in vars_in_section:
            default_value = var['default_value']
            markdown += f"| `{var['var_name']}` | {default_value} | {var['description']} |\n"
    return markdown

# Usage
import inspect
from ibeam.src import var

src = inspect.getsource(var).split('\n')
variables = parse_var_py(src)
markdown = generate_markdown(variables)
print(markdown)
