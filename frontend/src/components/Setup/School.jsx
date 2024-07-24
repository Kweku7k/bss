import React, { useState } from 'react'
import { Table } from 'react-bootstrap';
import { BiEditAlt, BiTrashAlt } from 'react-icons/bi'
import Form from '../Forms/Form';
import DynamicTable from '../Forms/DynamicTable';



const School = () => {

    const [schools, setSchools] = useState([]);
    const [currentSchool, setCurrentSchool] = useState(null);

    const formFields = [
        { id: 'school_name', label: 'Name of School', type: 'text', placeholder: 'Enter school name' },
        { id: 'school_code', label: 'Short Name', type: 'text', placeholder: 'Enter short name' },
        { id: 'school_location', label: 'Location', type: 'text', placeholder: 'Enter location' },
        { id: 'school_type', label: 'Level of School', type: 'select', options: [
          { value: 'BS', label: 'Basic School' },
          { value: 'SS', label: 'Secondary School' },
          { value: 'TC', label: 'Post Secondary School' },
          { value: 'UN', label: 'University' }
        ]}
    ];

   

  return (
    <div className="row">
        <div className="col-lg-5">
        <Form
          title={currentSchool !== null ? 'Edit School' : 'Add New School'}
          fields={formFields}
          initialData={currentSchool !== null ? schools.find(school => school.id === currentSchool) : {}}
          data={schools}
          setData={setSchools}
          currentDataIndex={currentSchool}
          setCurrentDataIndex={setCurrentSchool}
          apiUrl={currentSchool !== null ? `school/${currentSchool}` : "school"}  // Dynamic URL for editing or adding
          method={currentSchool !== null ? 'PUT' : 'POST'}  // Method based on action
        />
        </div>

        <div className="col-lg-7">
            <DynamicTable
                apiUrl="api/school"
                data={schools}
                fields={formFields}
                setData={setSchools}
                setCurrentDataIndex={setCurrentSchool}
            />
        </div>
    </div>
  )
}

export default School